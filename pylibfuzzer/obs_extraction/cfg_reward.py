import json
import shelve
from struct import iter_unpack
from typing import List

import networkx as nx
import numpy as np
from tqdm import tqdm

from pylibfuzzer.obs_extraction.base import BaseExtractor, RewardExtractor


class CfgRewardExtractor(BaseExtractor, RewardExtractor):
    def __init__(self, path='controlflowgraph.json'):
        with shelve.open(f'{__class__}.cache') as s:
            if 'graph' not in s or 'inv_mapping' not in s:
                with open(path) as f:
                    d = json.load(f)

                graph = {int(k): set(v['children']) for k, v in d.items()}
                mapping = {int(k): set(v['jazzerids']) for k, v in d.items() if v['jazzerids']}
                s['inv_mapping'] = {jazzer: soot for soot, jazzerids in mapping.items() for jazzer in jazzerids}
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

                s['graph'] = graph

            graph = s['graph']
            self.inv_mapping = s['inv_mapping']

            if 'ranks' not in s:
                G = nx.DiGraph()
                G.add_edges_from([(u, v) for u, vs in graph.items() for v in vs])
                s['ranks'] = nx.pagerank(G)
            self.ranks = s['ranks']

    def extract_obs(self, b: bytes) -> float:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        covered_branches = set(np.nonzero(np.fromiter((stru[0] for stru in iter_unpack('B', b)), int, len(b)))[0])
        reward = sum((self.ranks.get(self.inv_mapping.get(i, None), 0) for i in covered_branches))
        return reward

    def extract_multi_obs(self, bs: List[bytes]) -> float:
        return np.array([self.extract_obs(b) for b in bs]).mean()
