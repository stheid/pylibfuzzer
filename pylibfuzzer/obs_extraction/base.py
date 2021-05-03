from typing import Any


class BaseExtractor:
    def extract_obs(self, b: bytes) -> Any:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        pass
