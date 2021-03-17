import importlib

import yaml


def main(conf='fuzzer.yml'):
    with open(conf, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    fuzzer_conf = config.get('fuzzer')

    # fuzzer class
    clsname = fuzzer_conf.pop('cls')
    module = importlib.import_module('pylibfuzzer.algos')
    cls = getattr(module, clsname)

    # fuzzerparams
    fuzzer = cls(**fuzzer_conf)

    return fuzzer


if __name__ == '__main__':
    main()
