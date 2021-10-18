import numpy as np
import pytest

from pylibfuzzer.input_generators.sparks.sparks_algo import SparksFuzzer


@pytest.fixture
def fuzzer():
    return SparksFuzzer('input_generators/sparks/gram.yml', startword='S', population_size=10)


def test_sparks_seed(fuzzer):
    fuzzer.load_seed([])
    assert len(fuzzer.create_inputs()) == 10


def test_sparks_mutate(fuzzer):
    fuzzer.load_seed([])
    fuzzer.create_inputs()
    fuzzer.observe(np.random.uniform(size=10).tolist())  # noqa
    assert len(fuzzer.create_inputs()) == 10
