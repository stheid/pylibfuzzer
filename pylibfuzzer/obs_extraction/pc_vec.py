from struct import iter_unpack

import numpy as np

from pylibfuzzer.obs_extraction.base import BaseExtractor


class PcVectorExtractor(BaseExtractor):
    def extract_obs(self, b: bytes) -> np.ndarray:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        return np.fromiter((stru[0] for stru in iter_unpack('B', b)), int, len(b))
