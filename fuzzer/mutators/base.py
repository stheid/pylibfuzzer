import numpy as np


class Mutator:
    def __init__(self, seed=None):
        self.rng = np.random.default_rng(seed)  # type: np.random.Generator

    def mutate(self, b: bytearray) -> bytearray:
        pass
