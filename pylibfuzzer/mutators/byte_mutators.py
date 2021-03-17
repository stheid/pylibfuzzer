from .base import Mutator


class SubstituteByteMutator(Mutator):
    def mutate(self, b: bytearray) -> bytearray:
        pos = self.rng.integers(0, len(b))
        byte = self.rng.bytes(1)[0]
        b[pos] = byte
        return b


class DeleteByteMutator(Mutator):
    def mutate(self, b: bytearray) -> bytearray:
        pos = self.rng.integers(0, len(b))
        del b[pos]
        return b


class AddByteMutator(Mutator):
    def mutate(self, b: bytearray) -> bytearray:
        pos = self.rng.integers(0, len(b))
        byte = self.rng.bytes(1)[0]
        return b[:pos] + byte + b[pos:]
