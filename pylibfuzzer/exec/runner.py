import importlib

import click
import yaml


@click.command()
@click.option('--conf', default='fuzzer.yml', help='Fuzzer configuration file.')
def main(conf):
    with open(conf, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    fuzzer_conf = config.get('fuzzer')

    # fuzzer class
    clsname = fuzzer_conf.pop('cls')
    module = importlib.import_module('fuzzer.algos')
    cls = getattr(module, clsname)

    # fuzzerparams
    fuzzer = cls(**fuzzer_conf)

    return fuzzer


if __name__ == '__main__':
    main()
