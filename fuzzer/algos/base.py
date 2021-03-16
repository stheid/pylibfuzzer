import importlib
from typing import Optional, Union, Callable

from fuzzer.fitness import cov_fitness
from fuzzer.mutators import SubstituteByteMutator, AddByteMutator, DeleteByteMutator


class BaseFuzzer:
    def __init__(self, fitness: Optional[Union[Callable, str]] = None):
        if fitness is None:
            self.fitness = cov_fitness
        elif isinstance(fitness, Callable):
            self.fitness = fitness
        else:
            module = importlib.import_module('fuzzer.fitness')
            self.fitness = getattr(module, fitness)

    def load_seed(self, path):
        """
        loads all files in the seed to the model

        :param path:
        :return:
        """
        pass

    def create_input(self) -> list[bytes]:
        """
        create new input from internal model

        in most implementations the first couple of inputs from this functions will be the seed files

        :return: list of files as bytes
        """
        pass

    def observe(self, fuzzing_result: list[bytes]):
        """
        gets execution results of the last input batch passed to the PUT.

        :param fuzzing_result:
        :return:
        """
        pass


class MutationBasedFuzzer(BaseFuzzer):
    def __init__(self, mutators: list[str] = None, fitness: Optional[Union[Callable, str]] = None, seed=None):
        super().__init__(fitness)
        if mutators is None:
            mutators = [SubstituteByteMutator(seed), AddByteMutator(seed), DeleteByteMutator(seed)]
        else:
            module = importlib.import_module('fuzzer.mutators')
            mutators = [getattr(module, mut)(seed) for mut in mutators]
        self.mutators = [mut.mutate for mut in mutators]
