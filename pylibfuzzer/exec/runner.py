import importlib
import json
import logging
from datetime import datetime
from glob import glob
from os.path import isfile
from pathlib import Path
from typing import List
from uuid import uuid1

import click
import numpy as np
import tensorflow as tf
import yaml
from tqdm import tqdm

import pylibfuzzer.util.dict as dutil
from pylibfuzzer.exec.dispatcher import Dispatcher
from pylibfuzzer.input_generators.base import BaseFuzzer
from pylibfuzzer.obs_transform import Pipeline, Reward, SocketCoverageTransformer
from pylibfuzzer.util.dataset.datasetio import DatasetIO
from pylibfuzzer.util.timer import timer

logger = logging.getLogger(__name__)


@click.command()
@click.option('--conf', default=['experiment.yml'], multiple=True, help='configuration yaml')
@click.option('--log_suff', default='', help='logging folder suffix')
def main(conf, log_suff, **kwargs):
    Runner(conf, log_suff, **kwargs).run()


class Runner:
    def __init__(self, configs, suffix='', **kwargs):
        self.__start_time = datetime.now()
        self._seed_files = []
        self.i = 0

        def read_config(conf):
            with open(conf, 'r') as stream:
                try:
                    config_ = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
            return config_

        if isinstance(configs, str):
            configs = [configs]
        confs = [read_config(conf) for conf in configs] + [dutil.ravel(kwargs)]
        config = dutil.mergeall(confs)

        confname = ';'.join(configs)
        # EXPORTING needs to take place before elements are popd out below
        self.logdir = Path('logs') / f'{datetime.now().strftime("%Y.%m.%d-%H:%M:%S.%f")} {suffix or confname}'
        self.summarywriter = tf.summary.create_file_writer(str(self.logdir))
        with open(Path(self.logdir) / confname, 'w') as f:
            yaml.dump(config, f)

        # |RUNNER|
        runner_conf = config.get('runner', dict())
        self.time_budget = runner_conf.get('time_budget', None)
        self.limit = runner_conf.get('limit', None)
        self.do_warmup = runner_conf.get('warmup', True)
        loglevel = runner_conf.get('loglevel', logging.WARNING)
        self.corpusdir = runner_conf.get('corpusdir', None)
        self.crashdir = runner_conf.get('crashdir', None)
        self.cov_extractor = SocketCoverageTransformer()
        logging.basicConfig(level=loglevel)
        logger.debug(config)
        self.rewards = []
        self.export_data = runner_conf.get('export_data', False)
        fuzz_target = runner_conf.get('fuzz_target', [])

        # |FUZZER|
        fuzzer_conf = config.get('fuzzer')

        # fuzzer class
        clsname = fuzzer_conf.pop('cls')
        module = importlib.import_module('pylibfuzzer.input_generators')
        cls = getattr(module, clsname)

        # create fuzzer
        self.input_generator = cls(**fuzzer_conf)  # type: BaseFuzzer

        # |DISPATCHER|
        dispatcher_cfg = config.get('dispatcher')

        # dispatcher class
        module = importlib.import_module('pylibfuzzer.exec.dispatcher')
        clsname = dispatcher_cfg.pop('type') + 'Dispatcher'
        cls = getattr(module, clsname)

        # create pipeline
        transformers = config.get('obs_transformation')
        module = importlib.import_module('pylibfuzzer.obs_transform')
        pipeline = []
        for trans_cfg in transformers:
            clsname = (trans_cfg.pop('type') + 'Transformer')
            pipeline.append(getattr(module, clsname)(**trans_cfg))
        self.pipeline = Pipeline(pipeline)

        # validate algorithm with pipeline
        if self.input_generator.obs_type != List[self.pipeline.output_type]:  # noqa
            raise RuntimeError(
                f'{self.input_generator} and {self.pipeline} are not compatible. Please check your configuration file.')

        # create fuzzer
        if 'jazzer_cmd' in dispatcher_cfg:
            dispatcher_cfg['jazzer_cmd'] += fuzz_target
        if 'logfile' in dispatcher_cfg:
            dispatcher_cfg['logfile'] = Path(self.logdir) / dispatcher_cfg['logfile']
        self.dispatcher = cls(self, **dispatcher_cfg)  # type: Dispatcher

        # |SEED FILES|
        self.seed_files = config.get('seed_files')

    def run(self):
        # execute the main loop
        self.input_generator.prepare()
        self.input_generator.load_seed(self.seed_files)

        with self.dispatcher as cmd, \
                self.input_generator, \
                self.summarywriter.as_default(), \
                tqdm(total=self.limit) as pbar, \
                DatasetIO(self.logdir, dry_run=not self.export_data) as dataset_collector:

            def poll_jazzer():
                if cmd.proc.poll() is not None:
                    raise RuntimeError("jazzer died")

            self.pipeline.prepare(onbusy_callback=poll_jazzer)

            while not (self.input_generator.done() or self.timeout or self.overiter):
                # create inputs
                logger.info('Creating input batch starting with number %d ', self.i)
                with timer() as elapsed:
                    batch = self.input_generator.create_inputs()
                batchsize = len(batch)
                pbar.update(batchsize)
                tf.summary.scalar('time/create-input', elapsed() / batchsize, step=self.i)

                file_sizes = np.array([len(file) for file in batch])
                tf.summary.scalar('input/length-avg', file_sizes.mean(), step=self.i)
                tf.summary.scalar('input/length-std', file_sizes.std(), step=self.i)

                # execute inputs
                if self.do_warmup:
                    # if warmup is enabled the first input will be executed twice on the PUT,
                    # to warm up the jazzer and get more consistent coverage information
                    cmd.post(batch[0])
                    self.do_warmup = False

                logger.info('Executing input batch starting with number %d ', self.i)
                results = []
                for j, created_input in enumerate(tqdm(batch, disable=len(batch) == 1, leave=False)):
                    idx = self.i + j
                    logger.debug('Executing input number %d ', idx)
                    with timer() as elapsed:
                        covs, is_not_crashed = cmd.post(created_input)
                    tf.summary.scalar('time/exec-put', elapsed(), step=idx)

                    # all the other entries in results are from multi-exec and not under our control.
                    created_input_cov = covs[0]
                    is_input_crash = not is_not_crashed[0]
                    self.cov_extractor(created_input_cov)
                    if self.cov_extractor.coverage_increased:
                        tf.summary.scalar('out/coverage', len(self.cov_extractor.total_coverage), step=idx)

                        # write corpus
                        if self.corpusdir is not None:
                            with open(Path(self.corpusdir) / str(uuid1()), 'wb') as f:
                                f.write(created_input)

                        # write crash
                        if self.crashdir is not None and is_input_crash:
                            with open(Path(self.corpusdir) / str(uuid1()), 'wb') as f:
                                f.write(created_input)
                    # using only the list of coverages and discarding the
                    results.append(self.pipeline.batch_transform(covs))

                    logger.debug("Exporting input number %d", idx)
                    dataset_collector.collect(idx, created_input, created_input_cov)

                # send observed result to input generator
                if self.pipeline.output_type == Reward:
                    for j, reward in enumerate(results):
                        tf.summary.scalar('reward', reward, self.i + j)
                        self.rewards.append(reward)
                self.i += batchsize
                self.input_generator.observe(results)

            if hasattr(self.pipeline, 'total_coverage'):
                with open('cov.json', 'w') as f:
                    json.dump(list(self.pipeline.total_coverage), f)

            if count := getattr(self.dispatcher, 'empty_coverages_count', 0):
                logger.warning(f'Number of empty coverages: {count}')

    @property
    def seed_files(self):
        return self._seed_files

    @seed_files.setter
    def seed_files(self, paths):
        if paths:
            if isinstance(paths, str):
                paths = [paths]
            for path in paths:
                if isfile(path):
                    self._seed_files.append(path)
                else:
                    self._seed_files.extend(glob(path + "/*", recursive=True))

    @property
    def timeout(self):
        return self.time_budget and (datetime.now() - self.__start_time).seconds >= self.time_budget

    @property
    def overiter(self):
        return self.limit and self.i >= self.limit


if __name__ == '__main__':
    main()
