import networkx as nx
import numexpr as ne
import numpy as np

from pylibfuzzer.obs_transform.pipeline import Transformer, CovSet, Reward
from .util import digraph_from_jgrapht


class CFGRewardTransformer(Transformer):
    def __init__(self, path='icfg.json'):
        super().__init__()
        self.G = digraph_from_jgrapht(path)

        self.ranks = nx.pagerank(self.G)

    def __call__(self, data: CovSet) -> Reward:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        reward = sum((self.ranks.get(i, 0) for i in data))
        return reward


class DirectedCFGRewardTransformer(CFGRewardTransformer):
    def __init__(self, path='icfg.json', goal=564, theta=None, use_pr_weigth=False):
        super().__init__(path=path)
        self.use_pr_weigth = use_pr_weigth
        self.goal = goal
        self.distances = nx.single_target_shortest_path(self.G, self.goal)
        if theta is None:
            self.theta = lambda x: np.exp(2 * x)
        elif isinstance(theta, str):
            self.theta = lambda x: ne.evaluate(theta)
        elif callable(theta):
            self.theta = theta
        else:
            raise RuntimeError("theta can't be evaluated as a function. Please check the configuration yaml")
        self.max_reward = self.reward(set(self.G))

    def __call__(self, data: CovSet) -> Reward:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        return self.reward(data) / self.max_reward

    def reward(self, covered_branches: set):
        reward = sum((
            (self.ranks.get(id_, 0) if self.use_pr_weigth else 1) /
            (self.theta(self.get_dist_or_inf(id_)) + 1e-10)
            for id_ in covered_branches if id_ in self.G))
        return reward

    def get_dist_or_inf(self, id_):
        path = self.distances.get(id_, None)
        if path is None:
            return float('inf')
        return len(path) - 1
