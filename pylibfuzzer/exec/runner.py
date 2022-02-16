import importlib
import json
import logging
import os
import shutil
from datetime import datetime
from glob import glob
from os.path import isfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
from uuid import uuid1

import click
import numpy as np
import tensorflow as tf
import yaml
from tqdm import tqdm

import pylibfuzzer.util.dict as dutil
from pylibfuzzer.exec.dispatcher.base import BaseDispatcher
from pylibfuzzer.input_generators.base import BaseFuzzer
from pylibfuzzer.obs_transform import Pipeline, Reward, SocketCoverageTransformer
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
                    config = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
            return config

        if isinstance(configs, str):
            configs = [configs]
        confs = [read_config(conf) for conf in configs] + [dutil.ravel(kwargs)]
        config = dutil.mergeall(confs)

        confname = ';'.join(configs)
        # EXPORTING needs to take place before elements are popd out below
        self.logdir = f'logs/{datetime.now().strftime("%Y.%m.%d-%H:%M:%S.%f")} ' + (suffix or confname)
        self.summarywriter = tf.summary.create_file_writer(self.logdir)
        with open(Path(self.logdir) / confname, 'w') as f:
            yaml.dump(config, f)

        # |RUNNER|
        runner_conf = config.get('runner', dict())
        self.time_budget = runner_conf.get('time_budget', None)
        self.limit = runner_conf.get('limit', None)
        self.do_warmup = runner_conf.get('warmup', True)
        loglevel = runner_conf.get('loglevel', logging.WARNING)
        self.corpusdir = runner_conf.get('corpusdir', None)
        self.cov_extractor = SocketCoverageTransformer()
        logging.basicConfig(level=loglevel)
        logger.debug(config)
        self.rewards = []
        self.dataset_file_prefix = runner_conf.get('dataset_file_prefix', None)
        fuzz_target = runner_conf.get('fuzz_target', [])

        # |FUZZER|
        fuzzer_conf = config.get('fuzzer')

        # fuzzer class
        clsname = fuzzer_conf.pop('cls')
        module = importlib.import_module('pylibfuzzer.input_generators')
        cls = getattr(module, clsname)

        # create fuzzer
        if 'jazzer_cmd' in fuzzer_conf:
            fuzzer_conf['jazzer_cmd'] += fuzz_target
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
        if 'log_file' in dispatcher_cfg:
            dispatcher_cfg['log_file'] = Path(self.logdir) / dispatcher_cfg['log_file']
        self.dispatcher = cls(self, **dispatcher_cfg)  # type: BaseDispatcher
        if self.dispatcher.interfacetype != self.pipeline.input_type:
            raise RuntimeError(
                f'{self.dispatcher.__class__} and {self.pipeline.__class__} are not compatible'
                f' ({self.dispatcher.interfacetype} != {self.pipeline.input_type}).'
                f' Please check your configuration file.')

        # |SEED FILES|
        self.seed_files = config.get('seed_files')

    def run(self):
        # execute the main loop
        self.input_generator.load_seed(self.seed_files)
        with self.dispatcher as cmd, self.input_generator, self.summarywriter.as_default(), TemporaryDirectory() as dataset_dir:
            while not (self.input_generator.done() or self.timeout or self.overiter):

                # create inputs
                logger.info('Creating input batch starting with number %d ', self.i)
                with timer() as elapsed:
                    batch = self.input_generator.create_inputs()
                batchsize = len(batch)
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
                for j, created_input in enumerate(tqdm(batch)):
                    idx = self.i + j
                    logger.debug('Executing input number %d ', idx)
                    with timer() as elapsed:
                        result = cmd.post(created_input)
                    tf.summary.scalar('time/exec-put', elapsed(), step=idx)

                    # all the other entries in results are from multi-exec and not under our control.
                    created_input_cov = result[0]
                    self.cov_extractor(created_input_cov)
                    if self.corpusdir is not None and self.cov_extractor.coverage_increased:
                        with open(Path(self.corpusdir) / str(uuid1()), 'wb') as f:
                            f.write(created_input)
                    results.append(self.pipeline.batch_transform(result))

                    if self.dataset_file_prefix is not None:
                        logger.debug("Exporting input number %d", idx)
                        with open(Path(dataset_dir) / f"input_{idx}", 'wb') as f:
                            f.write(created_input)
                        with open(Path(dataset_dir) / f"cov_{idx}", 'wb') as f:
                            f.write(created_input_cov)

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

            if self.dataset_file_prefix is not None:
                logger.info('Compressing the dataset into a zip archive')
                shutil.make_archive(f'{self.dataset_file_prefix} – {datetime.now()}', 'zip', dataset_dir)

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
