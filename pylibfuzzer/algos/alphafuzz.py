import logging
from collections import Counter
from typing import Optional, List

import numpy as np

from pylibfuzzer.algos.base import MutationBasedFuzzer


class AlphaFuzz(MutationBasedFuzzer):
    def __init__(self):
        super().__init__()

        # root node
        self.tree = None
        # currently expanded and evaluated node
        self.curr = None

    def load_seed(self, path):
        pass
        # create seed root and append seed inputs as children

    def create_inputs(self) -> List[bytes]:
        # ask root for "best_scoring"
        # mutate
        pass

    def observe(self, fuzzing_result: List[bytes]):
        # create new node with input and coverage information
        # add es child of self.curr
        pass


class Node:
    c = 2

    def __init__(self, input: bytes, trace: Optional[Counter] = None, children: Optional[List['Node']] = None):
        self.input = input
        self.parent = None
        self.node_trace = trace or Counter()  # type: Counter
        self.children = children or []  # type: List['Node']
        self.tree_trace = self.node_trace + (sum([child.tree_trace for child in self.children], Counter()))
        for child in self.children:
            child.parent = self
        self.n = 0

    def append_child(self, nodes: List['Node']):
        self.children.extend(nodes)
        for node in nodes:
            node.parent = self
        self.tree_trace = self.tree_trace + sum([node.node_trace for node in nodes], Counter())
        # increment the nodes count since it has been selected as seed in the previous round

        if self.parent is not None:
            self.n = self.n + 1

    def best_node(self) -> 'Node':
        try:
            locally_best = max([self] + self.children, key=lambda x: x.score)
            if locally_best is not self:
                return locally_best.best_node()
            return self
        except ValueError:
            return self

    @property
    def score(self):
        # number of rare branches covered
        if self.parent is None:
            return 0
        min_ = min(self.parent.tree_trace.values())
        rare_branches = {k for k, v in self.parent.tree_trace.items() if v == min_}
        added_by_node = len(rare_branches & self.node_trace.keys())
        try:
            return added_by_node / self.n + (self.c * np.log(self.parent.n) / self.n) ** .5
        except ZeroDivisionError:
            if added_by_node == 0:
                return 1
            return float('inf')

    @property
    def n(self):
        return self._n

    @n.setter
    def n(self, val):
        if not hasattr(self, '_n'):
            self._n = 0
        diff = val - self._n
        self._n += diff

        if self.parent is not None:
            self.parent.n = self.parent.n + diff

    @property
    def tree_trace(self) -> Counter:
        return self._tree_trace

    @tree_trace.setter
    def tree_trace(self, trace: Counter):
        if not hasattr(self, '_tree_trace'):
            self._tree_trace = Counter()
        diff = trace - self._tree_trace
        self._tree_trace += diff

        if self.parent is not None:
            self.parent.tree_trace = self.parent.tree_trace + diff

    def __str__(self, depth=1):
        return_string = [repr(self)]
        for child in self.children:
            return_string.extend(["\n", "  " * (depth - 1) + ' └', child.__str__(depth + 1)])
        return "".join(return_string)

    def __repr__(self):
        return f"'{self.input.decode()}': \t{self.n} {dict(self.node_trace)}; {dict(self.tree_trace)}; {self.score:.2f}"


if __name__ == '__main__':
    seed = [(b'x', Counter({'b₀': 1})), (b'c', Counter({'b₅': 1}))]
    results = dict(xd=(b'xd', Counter({'b₀': 1, 'b₁': 1})),
                   ch=(b'ch', Counter({'b₅': 1, 'b₇': 1})),
                   xe=(b'xe', Counter({'b₀': 1, 'b₂': 1})),
                   xf=(b'xf', Counter({'b₀': 1, 'b₃': 1})))
    childs = dict(x=['xd', 'xe'],
                  xd=['xf'],
                  c=['ch'])

    logging.basicConfig(level=logging.DEBUG)

    # root node
    tree = Node(b'', None)
    [tree.append_child([Node(i, t)]) for i, t in seed]
    print(tree)

    while True:
        try:
            curr = tree.best_node()
            print(f'\nnext: {curr!r}')

            # mutate x
            mutated = [Node(*results[child]) for child in childs[curr.input.decode()]]
            print(f'adding: {mutated!r}\n')
            curr.append_child(mutated)

            print(tree)
        except IndexError:
            break
