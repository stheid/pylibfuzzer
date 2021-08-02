from struct import iter_unpack
from typing import Any, List

import numpy as np


class BaseExtractor:
    def __call__(self, *args, **kwargs):
        assert len(args) == 1
        return self.extract_multi_obs(args[0])

    def extract_obs(self, b: bytes) -> Any:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        pass

    def extract_multi_obs(self, bs: List[bytes]) -> Any:
        """

        :param bs: aggregate observations
        :return: observation similar to openAI gym
        """
        return self.extract_obs(bs[0])


class RewardMixin:
    def extract_obs(self, b: bytes) -> float:
        pass


class CovVectorMixin:
    def __init__(self):
        self.total_coverage = set()

    def to_coverage_vec_and_record(self, b: bytes) -> set:
        covered_branches = set(map(int,
                                   np.nonzero(np.fromiter((stru[0] for stru in iter_unpack('B', b)), int, len(b)))[0]))
        self.total_coverage.update(covered_branches)
        return covered_branches
