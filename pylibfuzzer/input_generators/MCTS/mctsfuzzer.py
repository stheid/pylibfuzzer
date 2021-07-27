import logging
from glob import glob
from pathlib import Path
from typing import List

import jpype
import jpype.imports

from pylibfuzzer.input_generators.base import BaseFuzzer
from pylibfuzzer.obs_extraction.base import RewardExtractor

logger = logging.getLogger(__name__)


class MCTSFuzzer(BaseFuzzer):
    supported_extractors = [RewardExtractor]

    def __init__(self, max_iterations=2, grammar='grammar.yaml', path_cutoff_length=20):
        super().__init__()

        # noinspection PyUnresolvedReferences
        # startJVM is the right function
        jars = glob(str(Path(__file__).parent / '*mcts*.jar'))
        if len(jars) != 1:
            raise RuntimeWarning('Please provide one and only one mcts backend library for the MCTS fuzzer')
        jpype.startJVM(classpath=[str(Path(__file__).parent / jars[0])])
        jpype.imports.registerDomain("isml.aidev")

        # noinspection PyUnresolvedReferences
        from java.lang import System
        # noinspection PyUnresolvedReferences
        from java.io import PrintStream, File
        # noinspection PyUnresolvedReferences
        System.setErr(PrintStream(File("ailibs.log")))  #
        # noinspection PyUnresolvedReferences
        from isml.aidev import Algorithm

        self.algo = Algorithm(max_iterations, grammar, path_cutoff_length)

        self._initialized = True

    def create_inputs(self) -> List[bytes]:
        return [bytes(self.algo.createInput())]

    def observe(self, rewards: List[float]):
        # TODO the MCTS currently aims to minimize loss, hence we have to give it a negative reward
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
