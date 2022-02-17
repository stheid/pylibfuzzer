import numpy as np
from pylibfuzzer.input_generators import NeuzzFuzzer

conf = 'experiment.yml'
log_stuff = True


def test_gen_mutations():
    seed = np.random.randint(0, 255, size=(1, 10), dtype=np.uint8)
    grads = np.random.uniform(-1, 1, size=(1, 10))
    up = NeuzzFuzzer.gen_mutations(candidate=seed, grad=grads, exp=2)
    assert len(up) > len(seed)
