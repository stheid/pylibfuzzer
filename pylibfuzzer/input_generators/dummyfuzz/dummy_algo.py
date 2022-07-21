from typing import List
import logging
from pylibfuzzer.input_generators.base import BaseFuzzer

logger = logging.getLogger(__name__)


class DummyFuzzer(BaseFuzzer):
    """
    This class implements a dummy fuzzer that uses seedfiles to calculate coverage.
    """

    def __init__(self, max_input_len=500):
        super().__init__()
        self._do_warmup = True
        self.batch = []
        self.max_input_len = max_input_len

    def load_seed(self, seedfiles):
        for file in seedfiles:
            with open(file, 'rb') as f:
                input = f.read()
            # cut and pad seedfiles to be exact self.max_input_length
            input = input[:self.max_input_len] + bytes(bytearray(max(0, self.max_input_len - len(input))))
            self.batch.append(input)

    def create_inputs(self) -> List[bytes]:
        """
        -  fill up with random inputs to match desired size
        :return:
        """
        if self._do_warmup:
            self._do_warmup = False
            return self.batch
