from struct import iter_unpack

import numpy as np

from .pipeline import Transformer, CovSet, SocketInput


class SocketCovArrayTransformer(Transformer):
    def __call__(self, b: SocketInput) -> np.ndarray:
        # get a boolean array of the bytes that we receive over the socket
        covered_branches = np.array(
            np.fromiter((stru[0] for stru in iter_unpack('B', b)), int, len(b)) > 0,
            dtype=float)
        return covered_branches
