import logging
import os
from subprocess import Popen, PIPE
from time import sleep

logger = logging.getLogger(__name__)


class PipeDispatcher:
    def __init__(self, runner, cmd):
        self.runner = runner
        self.cmd = cmd

    def __enter__(self):
        self.proc = Popen(self.cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        # clear all output in an non-blocking manner
        os.set_blocking(self.proc.stderr.fileno(), False)
        sleep(1)
        self.proc.stderr.read()
        os.set_blocking(self.proc.stderr.fileno(), True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def post(self, data: bytes) -> bytes:
        with open('file', 'wb') as f:
            f.write(data)
        self.proc.stdin.write(b'file\n')
        self.proc.stdin.flush()
        # record result line
        line = self.proc.stderr.readline()
        while True:
            try:
                self.runner.extract(line)
                break
            except Exception:
                line = self.proc.stderr.readline()
        logger.info(line)
        return line
