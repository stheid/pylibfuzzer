from glob import glob
from typing import Optional, Callable, Union, List

import numpy as np

from pylibfuzzer.algos.base import MutationBasedFuzzer


class HillClimbFuzzer(MutationBasedFuzzer):
    def __init__(self, mutators: List[str] = None, fitness: Optional[Union[Callable, str]] = None, seed=None):
        super().__init__(mutators, fitness, seed)
        self.rng = np.random.default_rng(seed)  # type: np.random.Generator
        self.best_so_far = None
        self.batch = []

    def load_seed(self, path):
        if path is None:
            self.batch.append(b'')
        else:
            for file in glob(path + "/*"):
                with open(file, 'rb') as f:
                    self.batch.append(f.read())
        self._initialized = True

    def create_inputs(self) -> List[bytes]:
        self._check_initialization()
        if self.batch:
            return self.batch
        mutate = self.rng.choice(self.mutators, 1)[0]

        self.batch.append(mutate(bytearray(self.best_so_far)))
        return self.batch

    def observe(self, fuzzing_result: List[bytes]):
        batch = self.batch + [self.best_so_far]
        self.batch = []

        self.best_so_far = max(batch, key=self.fitness)
