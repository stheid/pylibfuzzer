from .pipeline import Transformer


class SocketCovDummyTransformer(Transformer):
    def __call__(self, b) -> bytes:
        # get a byte array from over the socket and just return it.
        return b
