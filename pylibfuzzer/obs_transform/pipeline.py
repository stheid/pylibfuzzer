from itertools import tee
from typing import Any, List, Set

import numpy as np


# Type aliases for pipeline interfaces
class PipeInput(bytes):
    pass  # observations from the old pipe interface with libfuzzer


class SocketInput(bytes):
    pass  # observations from the new socket interface with libfuzzer


CovSet = Set[int]  # set of coverage ids
Reward = float


def pairwise(iterable):
    # from itertools import pairwise
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


class Transformer:
    """
    Transformers can be stateful, meaning their behaviour can change wrt. the data they see
    """

    def __call__(self, data: Any) -> Any:
        return data

    @property
    def input_type(self):
        # check the input type of the transformer
        return list(self.__call__.__annotations__.values())[0]  # noqa

    @property
    def output_type(self):
        # check the output type of the transformer
        return self.__call__.__annotations__['return']  # noqa


class Pipeline:
    """
    As Transformers can be stateful, Pipelines can be stateful as well
    """

    def __init__(self, pipeline: List[Transformer], agg='mean'):
        self.validate(pipeline)
        try:
            getattr(np.array([]), agg)
            self.agg = agg
        except AttributeError:
            raise RuntimeError(f'numpy.array does not know such an aggregation function {agg}')
        self.pipeline = pipeline or [Transformer()]  # if pipeline empty, set a dummy transformer
        self.contained_attr = None

    @staticmethod
    def validate(pipeline):
        for trans in pipeline:
            if not isinstance(trans, Transformer):
                raise RuntimeError(f'"{trans}" is not a Transformer. Pipeline must consist of Transformers only.')
        for trans1, trans2 in pairwise(pipeline):
            if trans1.output_type != trans2.input_type:
                raise RuntimeError(
                    f'"{trans1}" and "{trans2}" don\'t implement a matching interface: "'
                    f'"{trans1.output_type}" != "{trans2.input_type}"')

    @property
    def input_type(self):
        # check the input type of the first transformer
        return self.pipeline[0].input_type

    @property
    def output_type(self):
        # check the output type of the last transformer
        return self.pipeline[-1].output_type

    def transform(self, observation):
        for trans in self.pipeline:
            observation = trans(observation)
        return observation

    def batch_transform(self, observations: list):
        return getattr(np.array([self.transform(observation) for observation in observations]), self.agg)()

    def __getattr__(self, item):
        if self.contained_attr is None:
            self.contained_attr = dict()
            # retrieve attributes
            for trans in self.pipeline:
                for attr in dir(trans):
                    if attr.startswith('__'):
                        continue  # ignore matic methods
                    # this will overwrite attributes if they exist already.
                    # this means if two transformers in a pipeline implement the same attribute
                    # only the one closer to the end of the pipeline will be available
                    self.contained_attr[attr] = getattr(trans, attr)
        try:
            return self.contained_attr.get(item)
        except KeyError:
            raise AttributeError(f'No element in {self.pipeline} contains the attribute {item}')


if __name__ == '__main__':
    print(Pipeline([]).output_type)
