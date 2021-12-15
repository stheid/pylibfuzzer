import pytest
import numpy as np
from pylibfuzzer.input_generators import NeuzzFuzzer
from pylibfuzzer.exec.runner import Runner
from pylibfuzzer.obs_transform.socket_cov_array import SocketCovArrayTransformer
from pylibfuzzer.exec.dispatcher.sock import SocketMultiDispatcher
from pylibfuzzer.obs_transform import Pipeline

conf = 'experiment.yml'
log_stuff = True


def test_gen_mutations():
    seed = np.random.randint(0, 255, size=(1, 10), dtype=np.uint8)
    grads = np.random.uniform(-1, 1, size=(1, 10))
    up = NeuzzFuzzer.gen_mutations(candidate=seed, grad=grads, exp=2)
    assert len(up) > len(seed)
