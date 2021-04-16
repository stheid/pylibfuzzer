import importlib
import logging
from datetime import datetime
from glob import glob
from os.path import isfile

import click
import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@click.command()
@click.option('--conf', default='fuzzer.yml', help='configuration yaml')
def main(conf):
    Runner(conf).run()


class Runner:
    def __init__(self, conf):
        self._seed_files = []
        self.i = 0

        # read config
        with open(conf, 'r') as stream:
            try:
                config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        # |FUZZER|
        fuzzer_conf = config.get('fuzzer')

        # fuzzer class
        clsname = fuzzer_conf.pop('cls')
        module = importlib.import_module('pylibfuzzer.algos')
        cls = getattr(module, clsname)

        # create fuzzer
        self.fuzzer = cls(**fuzzer_conf)

        # |DISPATCHER|
        dispatcher_cfg = config.get('dispatcher')

        # dispatcher class
        clsname = dispatcher_cfg.pop('type') + 'Dispatcher'
        module = importlib.import_module('pylibfuzzer.exec.dispatcher')
        cls = getattr(module, clsname)

        # create fuzzer
        self.dispatcher = cls(self, **dispatcher_cfg)

        # |SEED FILES|
        self.seed_files = config.get('seed_files')

        # |RUNNER|
        runner_conf = {**dict(time_budget=None, limit=None), **config.get('runner', dict())}
        self.time_budget = runner_conf['time_budget']
        self.limit = runner_conf['limit']

    def run(self):
        # execute the main loop
        self.fuzzer.load_seed(self.seed_files)

        with self.dispatcher as cmd:
            while not (self.fuzzer.done() or self.timeout or self.overiter):
                logger.info('Creating input number %d ', self.i)
                batch = self.fuzzer.create_inputs()
                self.i += len(batch)
                self.fuzzer.observe([cmd.post(bytes(data)) for data in batch])

    @property
    def seed_files(self):
        return self._seed_files

    @seed_files.setter
    def seed_files(self, paths):
        if paths:
            for path in paths:
                if isfile(path):
                    self._seed_files.append(path)
                else:
                    self._seed_files.extend(glob(path + "/*", recursive=True))

    @property
    def timeout(self):
        if not hasattr(self, '__start_time'):
            self.__start_time = datetime.now()
        return self.time_budget and (datetime.now() - self.__start_time).seconds >= self.time_budget

    @property
    def overiter(self):
        return self.limit and self.i >= self.limit


if __name__ == '__main__':
    main()
