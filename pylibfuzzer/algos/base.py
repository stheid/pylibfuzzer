import importlib
from typing import Optional, Union, Callable, List

import numpy as np

from pylibfuzzer.fitness import cov_fitness
from pylibfuzzer.mutators import SubstituteByteMutator, AddByteMutator, DeleteByteMutator


class BaseFuzzer:
    supported_extractors = []

    def __init__(self, fitness: Optional[Union[Callable, str]] = None):
        if fitness is None:
            self.fitness = cov_fitness
        elif isinstance(fitness, Callable):
            self.fitness = fitness
        else:
            module = importlib.import_module('pylibfuzzer.fitness')
            self.fitness = getattr(module, fitness)

        self._initialized = False

    def _check_initialization(self):
        """
        Checks whether the fuzzer implementation is initialized.
        Must be overwritten by fuzzers that need initialization

        :return:
        """
        if not self._initialized:
            raise RuntimeError(
                'please call load_seed() before creating the first input to initialize the internal state')

    def load_seed(self, path):
        """
        loads all files in the seed to the model

        :param path:
        :return:
        """
        pass

    def create_inputs(self) -> List[bytes]:
        """
        create new input from internal model

        in most implementations the first couple of inputs from this functions will be the seed files

        :return: list of files as bytes
        """
        return []

    def observe(self, fuzzing_result: List[bytes]):
        """
        gets execution results of the last input batch passed to the PUT.

        :param fuzzing_result:
        :return:
        """
        pass

    def done(self) -> bool:
        """
        returns true iff the fuzzer wants to terminate execution.

        :return:
        """
        return False

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MutationBasedFuzzer(BaseFuzzer):
    def __init__(self, mutators: List[str] = None, fitness: Optional[Union[Callable, str]] = None, seed=None):
        super().__init__(fitness)
        self.rng = np.random.default_rng(seed)  # type: np.random.Generator
        if mutators is None:
            mutators = [SubstituteByteMutator(seed), AddByteMutator(seed), DeleteByteMutator(seed)]
        else:
            module = importlib.import_module('pylibfuzzer.mutators')
            mutators = [getattr(module, mut)(seed) for mut in mutators]
        self.mutators = [mut.mutate for mut in mutators]
        self.batch = []

    def load_seed(self, seedfiles):
        self._initialized = True
        if not seedfiles:
            self.batch = [b'']
        for path in seedfiles:
            with open(path, 'rb') as f:
                self.batch.append(f.read())
