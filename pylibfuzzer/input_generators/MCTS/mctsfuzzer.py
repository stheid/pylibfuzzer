import logging
from glob import glob
from pathlib import Path
from subprocess import run, DEVNULL
from typing import List

import jpype
import jpype.imports

from pylibfuzzer.input_generators.base import BaseFuzzer

from pylibfuzzer.obs_transform import Reward

logger = logging.getLogger(__name__)


class MCTSFuzzer(BaseFuzzer):
    def __init__(self, max_iterations=2, grammar='grammar.yaml', path_cutoff_length=20):
        super().__init__()

        # startJVM is the right function
        logger.info('Compiling MCTS-Fuzzer')
        project_path = Path(__file__).parent / 'mcts-fuzzer'
        run(['./gradlew', ':shadow'], cwd=project_path, stdout=DEVNULL, stderr=DEVNULL)
        jar = glob(str(project_path / 'build' / 'libs' / '*all.jar'))[0]  # type:str

        logger.info('Starting JVM')
        # noinspection PyUnresolvedReferences
        jpype.startJVM('-Xmx10G', classpath=[jar])
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
