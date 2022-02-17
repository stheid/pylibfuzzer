from struct import iter_unpack

import numpy as np

from .pipeline import Transformer, CovSet


class SocketCoverageTransformer(Transformer):
    def __init__(self):
        self.total_coverage = set()
        self.coverage_increased = False

    def __call__(self, b) -> CovSet:
        covered_branches = set(
            map(int,
                np.nonzero(
                    np.fromiter((stru[0] for stru in iter_unpack('B', b)), int, len(b)))[0]))
        self.coverage_increased = not self.total_coverage.issuperset(covered_branches)
        self.total_coverage.update(covered_branches)
        return covered_branches
