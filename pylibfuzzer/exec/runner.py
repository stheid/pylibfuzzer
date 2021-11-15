import importlib
import json
import logging
from datetime import datetime
from glob import glob
from os.path import isfile
from pathlib import Path
from typing import List

import click
import tensorflow as tf
import yaml

import pylibfuzzer.util.dict as dutil
from pylibfuzzer.exec.dispatcher.base import BaseDispatcher
from pylibfuzzer.input_generators.base import BaseFuzzer
from pylibfuzzer.obs_transform import Pipeline, Reward
from pylibfuzzer.util.timer import timer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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
        self.dispatcher = cls(self, **dispatcher_cfg)  # type: BaseDispatcher
        if self.dispatcher.interfacetype != self.pipeline.input_type:
            raise RuntimeError(
                f'{self.dispatcher.__class__} and {self.pipeline.__class__} are not compatible'
                f' ({self.dispatcher.interfacetype} != {self.pipeline.input_type}).'
                f' Please check your configuration file.')

        # |SEED FILES|
        self.seed_files = config.get('seed_files')

        # |RUNNER|
        runner_conf = {**dict(time_budget=None, limit=None), **config.get('runner', dict())}
        self.time_budget = runner_conf['time_budget']
        self.limit = runner_conf['limit']
        self.do_warmup = runner_conf.get('warmup', True)
        self.rewards = []

    def run(self):
        # execute the main loop
        self.input_generator.load_seed(self.seed_files)

        with self.dispatcher as cmd, self.input_generator, self.summarywriter.as_default():
            while not (self.input_generator.done() or self.timeout or self.overiter):
                # create inputs
                logger.info('Creating input number %d ', self.i)
                with timer() as elapsed:
                    batch = self.input_generator.create_inputs()

                batchsize = len(batch)
                tf.summary.scalar('time/create-input', elapsed() / batchsize, step=self.i)
                for j, file in enumerate(batch):
                    tf.summary.scalar('input/length', len(file), step=self.i + j)

                # execute inputs
                if self.do_warmup:
                    # if warmup is enabled the first input will be executed twice on the PUT,
                    # to warm up the jazzer and get more consistent coverage information
                    cmd.post(batch[0])
                    self.do_warmup = False

                results = []
                for data in batch:
                    logger.info('Executing input number %d ', self.i)
                    with timer() as elapsed:
                        results.append(self.pipeline.batch_transform(cmd.post(data)))
                    tf.summary.scalar('time/exec-put', elapsed(), step=self.i)

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
