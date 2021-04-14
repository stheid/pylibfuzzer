import importlib
import logging

import click
import yaml

logging.basicConfig(level=logging.INFO)


@click.command()
@click.option('--conf', default='fuzzer.yml', help='configuration yaml')
def main(conf):
    Runner(conf).run()


class Runner:
    def __init__(self, conf):
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
        self.seedfiles = config.get('seed_files', [])

    def run(self):
        # execute the main loop
        self.fuzzer.load_seed(self.seedfiles)

        with self.dispatcher as cmd:
            while not self.fuzzer.done():
                batch = self.fuzzer.create_inputs()
                self.fuzzer.observe([cmd.post(data) for data in batch])


if __name__ == '__main__':
    main()
