from typing import Optional, Callable, Union, List

from pylibfuzzer.algos.base import MutationBasedFuzzer
from pylibfuzzer.obs_extraction import CovStrExtractor


class HillClimbFuzzer(MutationBasedFuzzer):
    supported_extractors = [CovStrExtractor]

    def __init__(self, mutators: List[str] = None, fitness: Optional[Union[Callable, str]] = None, seed=None):
        super().__init__(mutators, fitness, seed)
        self.best_so_far = None
        self.best_fittness = float('-inf')

    def create_inputs(self) -> List[bytes]:
        self._check_initialization()
        if self.batch:
            return self.batch
        mutate = self.rng.choice(self.mutators, 1)[0]

        self.batch.append(mutate(bytearray(self.best_so_far)))
        return self.batch

    def observe(self, fuzzing_result: list):
        batch = self.batch
        fitnesses = [self.fitness(res) for res in fuzzing_result]
        self.batch = []

        fittest = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        if best_fitness := fitnesses[fittest] > self.best_fittness:
            self.best_fittness = best_fitness
            self.best_so_far = batch[fittest]
