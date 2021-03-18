import importlib
from subprocess import Popen, PIPE

import yaml


def main(conf='fuzzer.yml', command=('/usr/bin/cat',), seed_path=None):
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

    proc = Popen(command, stdin=PIPE, stdout=PIPE)

    fuzzer.load_seed(seed_path)

    while not fuzzer.done():
        batch = fuzzer.create_inputs()
        results = []
        for data in batch:
            with open('file.dat', 'wb') as f:
                f.write(data)
            proc.stdin.write(b'file.dat\n')
            proc.stdin.flush()
            results.append(proc.stdout.readline())
        fuzzer.observe(results)
        print(results)


if __name__ == '__main__':
    main()
