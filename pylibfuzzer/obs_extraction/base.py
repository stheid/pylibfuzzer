from typing import Any, List


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

class RewardExtractor:
    def extract_obs(self, b: bytes) -> float:
        pass
