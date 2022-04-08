import numpy as np

from pylibfuzzer.util.array import remove_lsb


def test_remove_lsb_int():
    array = np.array([0,7,8,5])
    data = remove_lsb(array)
    assert data.tolist() == [0,4,8,4]

def test_remove_lsb_float():
    array = np.array([0.1,7.9, 8.1,4.8])
    data = remove_lsb(array)
    assert data.tolist() == [0,4,8,4]