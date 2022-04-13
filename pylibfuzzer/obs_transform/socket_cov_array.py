from struct import iter_unpack

import numpy as np

from .pipeline import Transformer


class SocketCovArrayTransformer(Transformer):
    def __call__(self, b) -> np.ndarray:
        # get a byte array from over the socket
        covered_branches = np.array(
            np.fromiter((stru[0] for stru in iter_unpack('B', b)), int, len(b)),
            dtype=float)
        return covered_branches
