import json
import shelve
from typing import List

import networkx as nx
import numexpr as ne
import numpy as np
from tqdm import tqdm

from pylibfuzzer.obs_extraction.base import BaseExtractor, RewardMixin, CovVectorMixin


class CfgRewardExtractor(BaseExtractor, RewardMixin, CovVectorMixin):
    def __init__(self, path='controlflowgraph.json', simplify=False, representatives=True):
        super().__init__()
        with shelve.open(f'{__class__}.cache') as s:
            if 'graph' not in s or 'id_to_node' not in s:
                with open(path) as f:
                    d = json.load(f)


                graph = {int(k): set(v['children']) for k, v in d.items()}
                mapping = {int(k): [v['jazzerids'][0]] if representatives else set(v['jazzerids'])
                           for k, v in d.items() if v['jazzerids']}
                s['id_to_node'] = {jazzer: soot for soot, jazzerids in mapping.items() for jazzer in jazzerids}
                if simplify:
                    self.simplify_graph(graph, mapping)

                s['graph'] = graph

            graph = s['graph']
            self.G = nx.DiGraph()
            # by adding only the edges, the graph only contains only edge-induced nodes. Singleton nodes are pruned
            self.G.add_edges_from([(u, v) for u, vs in graph.items() for v in vs])
            # also remove those unreachable nodes here (
            self.id_to_node = {id_: node for id_, node in s['id_to_node'].items() if node in self.G.nodes}
            print(sorted(self.id_to_node.keys()))

            if 'ranks' not in s:
                s['ranks'] = nx.pagerank(self.G)
            self.ranks = s['ranks']

    def simplify_graph(self, graph, mapping):
        nodes_to_remove = graph.keys() - mapping.keys()

        substitution = dict()

        # collapse the substitutions (O(n²))
        for node in tqdm(nodes_to_remove):
            value = graph[node]
            substitution[node] = value
            for from_, to_ in substitution.items():
                if node in to_:
                    substitution[from_] = to_ - {node} | value

        # apply substitutions can be done only once now
        for k, v in tqdm(substitution.items()):
            for from_, to_ in graph.items():
                if k in to_:
                    graph[from_] = to_ - {k} | v

    def extract_obs(self, b: bytes) -> float:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        covered_branches = self.to_coverage_vec_and_record(b)
        reward = sum((self.ranks.get(self.id_to_node.get(i, None), 0) for i in covered_branches))
        return reward

    def extract_multi_obs(self, bs: List[bytes]) -> float:
        return np.array([self.extract_obs(b) for b in bs]).mean()


class DirectedCFGRewardExtractor(CfgRewardExtractor):
    def __init__(self, path='controlflowgraph.json', goal=564, theta=None, simplify=False, use_pr_weigth=False):
        super().__init__(path=path, simplify=simplify)
        self.use_pr_weigth = use_pr_weigth
        self.goal = goal
        self.distances = nx.single_target_shortest_path(self.G, self.id_to_node[self.goal])
        if theta is None:
            self.theta = lambda x: np.exp(2 * x)
        elif isinstance(theta, str):
            self.theta = lambda x: ne.evaluate(theta)
        elif callable(theta):
            self.theta = theta
        else:
            raise RuntimeError("theta can't be evaluated as a function. Please check the configuration yaml")
        self.max_reward = self.reward(set(self.id_to_node.keys()))

    def extract_obs(self, b: bytes) -> float:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        covered_branches = self.to_coverage_vec_and_record(b)
        return self.reward(covered_branches) / self.max_reward

    def reward(self, covered_branches: set):
        reward = sum((
            (self.ranks.get(self.id_to_node[id_], 0) if self.use_pr_weigth else 1) /
            (self.theta(self.get_dist_or_inf(id_)) + 1e-10)
            for id_ in covered_branches if id_ in self.id_to_node))
        return reward

    def get_dist_or_inf(self, id_):
        path = self.distances.get(self.id_to_node[id_], None)
        if path is None:
            return float('inf')
        return len(path) - 1
