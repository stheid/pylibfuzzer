from typing import Optional, Callable, Union, List

from pylibfuzzer.input_generators.base import MutationBasedFuzzer
from pylibfuzzer.obs_extraction import CFGRewardExtractor, CovStrRewardExtractor


class HillClimbFuzzer(MutationBasedFuzzer):
    supported_extractors = [CovStrRewardExtractor, CFGRewardExtractor]

    def __init__(self, mutators: List[str] = None, seed=None):
        super().__init__(mutators, seed)
        self.best_so_far = None
        self.best_fittness = float('-inf')

    def create_inputs(self) -> List[bytes]:
        self._check_initialization()
        if self.batch:
            return self.batch
        mutate = self.rng.choice(self.mutators, 1)[0]

        self.batch.append(mutate(bytearray(self.best_so_far)))
        return self.batch

    def observe(self, rewards: list):
        batch = self.batch
        self.batch = []

        fittest = max(range(len(rewards)), key=lambda i: rewards[i])
        if best_fitness := rewards[fittest] > self.best_fittness:
            self.best_fittness = best_fitness
            self.best_so_far = batch[fittest]
