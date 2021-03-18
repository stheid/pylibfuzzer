from .base import SequenceMutator


class SubstituteByteMutator(SequenceMutator):
    def mutate(self, b: bytearray) -> bytearray:
        pos = self.pos(b)
        byte = self.rng.bytes(1)[0]
        if pos is None:
            return bytearray([byte])
        # if array emtpy (pos None) we will add at the beginning
        b[self.pos(b)] = byte
        return b


class DeleteByteMutator(SequenceMutator):
    def mutate(self, b: bytearray) -> bytearray:
        pos = self.pos(b)
        if pos is None:
            return b
        del b[pos]
        return b


class AddByteMutator(SequenceMutator):
    def mutate(self, b: bytearray) -> bytearray:
        # if array emtpy (pos None) we will add at the beginning
        pos = self.pos(b) or 0
        byte = self.rng.bytes(1)[0]
        return b[:pos] + bytearray([byte]) + b[pos:]
