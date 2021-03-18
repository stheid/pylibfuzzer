import importlib
import os
from subprocess import Popen, PIPE
from time import sleep

import yaml


def main(conf='fuzzer.yml', command=('./libpng_read_fuzzer', '-oracle=1', '-fork=1'), seed_path='seed.png'):
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

    proc = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    # clear all output in an non-blocking manner
    os.set_blocking(proc.stderr.fileno(), False)
    sleep(1)
    proc.stderr.read()
    os.set_blocking(proc.stderr.fileno(), True)
    fuzzer.load_seed(seed_path)

    while not fuzzer.done():
        batch = fuzzer.create_inputs()
        results = []
        for data in batch:
            with open('file', 'wb') as f:
                f.write(data)
            proc.stdin.write(b'file\n')
            proc.stdin.flush()
            # record result line
            line = proc.stderr.readline()
            while True:
                try:
                    fuzzer.fitness(line)
                    break
                except Exception:
                    line = proc.stderr.readline()
            results.append(line)

        fuzzer.observe(results)
        print(results)


if __name__ == '__main__':
    main()
