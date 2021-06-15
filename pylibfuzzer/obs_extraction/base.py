from typing import Any


class BaseExtractor:
    def __call__(self, *args, **kwargs):
        assert len(args) == 1
        return self.extract_obs(args[0])

    def extract_obs(self, b: bytes) -> Any:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        pass


class RewardExtractor:
    def extract_obs(self, b: bytes) -> float:
        pass
