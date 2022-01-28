import logging
from copy import deepcopy
from typing import List

import numpy as np

from pylibfuzzer.input_generators.base import BaseFuzzer
from pylibfuzzer.input_generators.sparks import Grammar
from pylibfuzzer.input_generators.sparks.individual import Individual
from pylibfuzzer.obs_transform import Reward

logger = logging.getLogger(__name__)


class SparksFuzzer(BaseFuzzer):
    """
    This class implements a GA type algorithm. The typical reward implementation of this class is stateful.
    to issue the reevaluation of rewards, we will re execute the inputs on the PUT to ease implementation.
    """

    def __init__(self, grammar_path, startword, population_size=100, elite_fraction=.1, survival_rate=.3,
                 crossover_share=1, resample_share=1):
        super().__init__()
        self._initialized = False
        self.grammar = Grammar(grammar_path, startword)

        self.population_size = population_size
        self.population = np.empty(self.population_size, dtype=Individual)
        self.fitnesses = []

        # the fraction of fittest individuals from last population to carry over
        self.elite_size = int(population_size * elite_fraction)
        self.survival_size = int(population_size * survival_rate)

        shares = crossover_share + resample_share
        self.crossover_size = int((self.population_size - self.survival_size) * crossover_share / shares)
        self.resample_size = self.population_size - self.survival_size - self.crossover_size

    def load_seed(self, seedfiles):
        pop = []
        for file in seedfiles:
            with open(file, 'rb') as f:
                pop.append(
                    Individual(grammar=self.grammar).from_pheno(f.read()))

        # Fill population with random trees
        # if there were more seedfiles than the population size allows,
        # those will be killed after the first observation
        for _ in range(len(pop), self.population_size):
            pop.append(Individual(self.grammar))
        self.population[:] = pop[:]

    def create_inputs(self) -> List[bytes]:
        if not self.fitnesses:
            # first iteration, so we need to execute the seedfiles!
            return [i.to_pheno() for i in self.population]
        fitnesses = np.array(self.fitnesses)
        if np.isnan(fitnesses.sum()):
            logger.error('fittness contains NaN values')

        # extract elite
        fitnesses_idx = np.argpartition(fitnesses, self.elite_size)
        elite = self.population[fitnesses_idx[:self.elite_size]]
        none_elite = self.population[fitnesses_idx[self.elite_size:]]

        # sample other parent individuals
        non_elite_fittness = (fitnesses[fitnesses_idx[self.elite_size:]]
                              / (fitnesses[fitnesses_idx[self.elite_size:]].sum()))
        rng = np.random.default_rng()
        other_survivors = rng.choice(none_elite, self.survival_size - self.elite_size, replace=False,
                                     p=non_elite_fittness)

        survivors = np.concatenate((elite, other_survivors))

        children = []
        for _ in range(self.crossover_size):
            parentA, parentB = rng.choice(survivors, 2, replace=False)
            children.append(deepcopy(parentA).crossover(parentB))

        parents = rng.choice(survivors, self.resample_size, replace=True)
        children.extend([deepcopy(parent).resample() for parent in parents])

        self.population = np.concatenate((survivors, np.array(children)))
        return [i.to_pheno() for i in self.population]

    def observe(self, fuzzing_result: List[Reward]):
        self.fitnesses = fuzzing_result
