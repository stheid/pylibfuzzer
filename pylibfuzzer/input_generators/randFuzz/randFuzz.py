from typing import List
import logging

import numpy as np
from tqdm import trange

from pylibfuzzer.input_generators.base import BaseFuzzer

logger = logging.getLogger(__name__)


class RandFuzzer(BaseFuzzer):
    """
    This class implements a random fuzzer that creates random inputs.
    """

    def __init__(self, max_input_len: int):
        super().__init__()
        self.batch = []
        self._do_warmup = True
        self.max_input_len = max_input_len

    def create_inputs(self) -> List[bytes]:
        """
        -  fill up with random inputs
        :return:
        """
        if self._do_warmup:
            self._do_warmup = False

            batch = self.batch
            # fill up with random inputs
            file_len = np.random.randint(self.max_input_len)
            batch.append(np.random.bytes(file_len) + bytes(bytearray(self.max_input_len - file_len)))

            self.batch = batch
        return self.batch
