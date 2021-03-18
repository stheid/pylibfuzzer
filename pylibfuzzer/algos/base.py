import importlib
from typing import Optional, Union, Callable, List

from pylibfuzzer.fitness import cov_fitness
from pylibfuzzer.mutators import SubstituteByteMutator, AddByteMutator, DeleteByteMutator


class BaseFuzzer:
    def __init__(self, fitness: Optional[Union[Callable, str]] = None):
        if fitness is None:
            self.fitness = cov_fitness
        elif isinstance(fitness, Callable):
            self.fitness = fitness
        else:
            module = importlib.import_module('pylibfuzzer.fitness')
            self.fitness = getattr(module, fitness)

    def is_initialized(self) -> bool:
        """
        Checks whether the fuzzer implementation is initialized.
        Must be overwritten by fuzzers that need initialization

        :return:
        """
        return True

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
        if not self.is_initialized():
            raise RuntimeError(
                'please call load_seed() before creating the first input to initialize the internal state')
        return []

    def observe(self, fuzzing_result: List[bytes]):
        """
        gets execution results of the last input batch passed to the PUT.

        :param fuzzing_result:
        :return:
        """
        pass

    def is_done(self) -> bool:
        """
        returns true iff the fuzzer wants to terminate execution.

        :return:
        """
        return False


class MutationBasedFuzzer(BaseFuzzer):
    def __init__(self, mutators: List[str] = None, fitness: Optional[Union[Callable, str]] = None, seed=None):
        super().__init__(fitness)
        if mutators is None:
            mutators = [SubstituteByteMutator(seed), AddByteMutator(seed), DeleteByteMutator(seed)]
        else:
            module = importlib.import_module('pylibfuzzer.mutators')
            mutators = [getattr(module, mut)(seed) for mut in mutators]
        self.mutators = [mut.mutate for mut in mutators]
