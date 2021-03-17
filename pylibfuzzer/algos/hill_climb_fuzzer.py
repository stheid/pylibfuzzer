from glob import glob
from typing import Optional, Callable, Union

import numpy as np

from pylibfuzzer.algos.base import MutationBasedFuzzer
from pylibfuzzer.fitness import cov_fitness


class HillClimbFuzzer(MutationBasedFuzzer):
    def __init__(self, mutators: list[str] = None, fitness: Optional[Union[Callable, str]] = None, seed=None):
        super().__init__(mutators, fitness, seed)
        self.rng = np.random.default_rng(seed)  # type: np.random.Generator
        self.best_so_far = None
        self.batch = []

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
