import re
from typing import Dict

from pylibfuzzer.obs_extraction import BaseExtractor


class CovStrExtractor(BaseExtractor):
    def extract_obs(self, b: bytes) -> Dict[str, int]:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        return {k: int(v) for k, v in [match.groups() for match in re.finditer(r'(\w+):\s*(\d+)', b.decode())]}
