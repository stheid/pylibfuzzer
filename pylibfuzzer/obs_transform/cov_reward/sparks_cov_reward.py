import logging
from collections import Counter

import numpy as np
from networkx import Graph

from pylibfuzzer.obs_transform.pipeline import Transformer, CovSet, Reward
from .util import digraph_from_jgrapht

logger = logging.getLogger(__name__)


class SparksRewardTransformer(Transformer):
    def __init__(self, path='icfg.json'):
        super().__init__()
        self.G = digraph_from_jgrapht(path)
        self.cov_counts = Counter()

    def __call__(self, data: CovSet) -> Reward:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        # update coverage bag
        self.cov_counts.update(data)

        # calculate induced subgraph from the cfg and the current covset
        subgraph = self.G.subgraph(data)  # type: Graph

        # calculate product of all directed edges:
        weights = [self.cov_counts[pred] / self.cov_counts[succ] for pred, succ in subgraph.edges()]

        # we will only count the weights that are actually smaller than 1 because only they will influence the product
        non_one_weights = max(1, len(list(filter(lambda x: x < 1, weights))))

        # 1/ nth_root(prod(weights)) to normalize the length of the coverage sequence
        ret = 1 / (np.prod(weights) ** (1 / non_one_weights))

        if np.isnan(ret):
            logger.warning('calculated NaN reward value. Falling back to 0 reward!')
            return 0
        return ret
