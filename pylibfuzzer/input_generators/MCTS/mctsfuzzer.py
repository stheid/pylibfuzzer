import logging
import os.path
from glob import glob
from pathlib import Path
from typing import List

import jpype
import jpype.imports

import pylibfuzzer
from pylibfuzzer.input_generators.base import BaseFuzzer

from pylibfuzzer.obs_transform import Reward

logger = logging.getLogger(__name__)


class MCTSFuzzer(BaseFuzzer):
    def __init__(self, mcts_fuzz_jar_pattern, jvm_args='-Xmx10G', max_iterations=2, grammar='grammar.yaml',
                 path_cutoff_length=20, headless=True):
        super().__init__()

        logger.info('Starting JVM')
        mcts_fuzz_jar = max(glob(mcts_fuzz_jar_pattern), key=os.path.getmtime)
        # startJVM is the right function
        # noinspection PyUnresolvedReferences
        jpype.startJVM(jvm_args, classpath=[mcts_fuzz_jar])
        jpype.imports.registerDomain("isml.aidev")

        # noinspection PyUnresolvedReferences
        from java.lang import System
        # noinspection PyUnresolvedReferences
        from java.io import PrintStream, File
        # noinspection PyUnresolvedReferences
        System.setErr(PrintStream(File("ailibs.log")))  #
        # noinspection PyUnresolvedReferences
        from isml.aidev import Algorithm

        self.algo = Algorithm(max_iterations, grammar, path_cutoff_length, headless)
        self.batch = []
        self.seedfiles_consumed = True
        self._initialized = True

    def load_seed(self, seedfiles):
        for file in seedfiles:
            with open(file, 'rb') as f:
                input = f.read()
            self.batch.append(input)
            self.seedfiles_consumed = False

    def create_inputs(self) -> List[bytes]:
        if self.batch:
            return [self.batch.pop(0)]
        self.seedfiles_consumed = True
        return [bytes(self.algo.createInput())]

    def observe(self, rewards: List[Reward]):
        if not self.seedfiles_consumed:
            return

        # MCTS aims to minimize loss, hence we have to give it a negative reward
        self.algo.observe(-rewards[0])
        # TODO efficiently check logs for errors
        # with open("ailibs.log") as f:
        #    if 'ERROR' in f.read():
        #        raise RuntimeError('AILibs reported an Error')

    def close(self):
        self.algo.join()
        # noinspection PyUnresolvedReferences
        # shutdownJVM is the right function, according to APIdoc
        jpype.shutdownJVM()


if __name__ == '__main__':
    MCTSFuzzer(grammar="/home/sheid/Project/pylibfuzzer/examples/jazzer_json/grammar.yaml")
