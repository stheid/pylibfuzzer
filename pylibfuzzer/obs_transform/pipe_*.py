import re
from typing import Dict, NewType

from pylibfuzzer.obs_transform import Reward, PipeInput
from pylibfuzzer.obs_transform.pipeline import Transformer

PipeInputDict = NewType('PipeInputDict', Dict[str, int])


class PipeDictTransformer(Transformer):
    def __call__(self, data: PipeInput) -> PipeInputDict:
        """

        :param data:
        :return: observation similar to openAI gym
        """
        return PipeInputDict(
            {k: int(v) for k, v in [match.groups() for match in re.finditer(r'(\w+):\s*(\d+)', data.decode())]})


class PipeDictRewardTransformer(Transformer):
    def __call__(self, data: PipeInputDict) -> Reward:
        """

        :param data:
        :return: observation similar to openAI gym
        """
        return data['cov']
