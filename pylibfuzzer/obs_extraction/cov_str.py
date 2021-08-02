import re
from typing import Dict

from pylibfuzzer.obs_extraction.base import BaseExtractor, RewardMixin


class CovStrExtractor(BaseExtractor):
    def extract_obs(self, b: bytes) -> Dict[str, int]:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        return {k: int(v) for k, v in [match.groups() for match in re.finditer(r'(\w+):\s*(\d+)', b.decode())]}


class CovStrRewardExtractor(CovStrExtractor, RewardMixin):
    def extract_obs(self, b: bytes) -> float:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        return super().extract_obs(b)['cov']
