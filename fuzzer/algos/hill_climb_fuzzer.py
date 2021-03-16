from glob import glob
from typing import Optional, Callable

import numpy as np

from fuzzer.algos.base import BaseFuzzer
from fuzzer.fitness import cov_fitness
from fuzzer.mutators import *


class HillClimbFuzzer(BaseFuzzer):
    def __init__(self, mutators: list[str] = None, fitness: Optional[Callable] = None, seed=None):
        super().__init__()
        self.rng = np.random.default_rng(seed)  # type: np.random.Generator
        self.best_so_far = None
        self.batch = []
        if mutators is None:
            mutators = [SubstituteByteMutator(seed), AddByteMutator(seed), DeleteByteMutator(seed)]
        else:
            # TODO resolve mutators from string
            mutators = []
        self.mutators = [mut.mutate for mut in mutators]
        self.fitness = fitness or cov_fitness

    def load_seed(self, path):
        for file in glob(path + "*"):
            with open(file, 'rb') as f:
                self.batch.append(f.read())

    def create_input(self) -> list[bytes]:
        if self.batch:
            return self.batch
        mutate = self.rng.choice(self.mutators, 1)

        self.batch.append(mutate(self.best_so_far))
        return self.batch

    def observe(self, fuzzing_result: list[bytes]):
        batch = self.batch + self.best_so_far
        self.batch = []

        self.best_so_far = max(batch, key=cov_fitness)
