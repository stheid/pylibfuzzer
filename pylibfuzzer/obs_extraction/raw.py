from struct import iter_unpack

import numpy as np

from pylibfuzzer.obs_extraction.base import BaseExtractor


class RawExtractor(BaseExtractor):
    def extract_obs(self, b: bytes) -> bytes:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        return b
