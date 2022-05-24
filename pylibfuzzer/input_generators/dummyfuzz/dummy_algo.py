from typing import List
import logging
import numpy as np
from tqdm import trange
from pylibfuzzer.input_generators.base import BaseFuzzer

logger = logging.getLogger(__name__)


class DummyFuzzer(BaseFuzzer):
    """
    This class implements a dummy fuzzer that uses seedfiles to calculate coverage.
    """

    def __init__(self, initial_dataset_len, max_input_len=500):
        super().__init__()
        self._do_warmup = True
        self.batch = []
        self.max_input_len = max_input_len
        self.initial_dataset_len = initial_dataset_len
        self.uncovered_bits = None

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

            batch = self.batch
            for _ in trange(len(batch), self.initial_dataset_len):
                file_len = np.random.randint(self.max_input_len)
                batch.append(np.random.bytes(file_len) + bytes(bytearray(self.max_input_len - file_len)))
            self.batch = batch
        return self.batch

    def observe(self, fuzzing_result: List[np.ndarray]):
        pass
