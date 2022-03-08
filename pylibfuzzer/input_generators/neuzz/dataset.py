from typing import Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)


class Dataset:
    def __init__(self, X: np.array = None, y: np.array = None,
                 max_size=10000, new_sw=2, weights=None):
        if X is None and y is None:
            self.X = np.array([])
            self.y = np.array([])
        elif len(X.shape) == 2 and len(y.shape) == 2:
            self.X = X
            self.y = y
        else:
            raise RuntimeError(f"X and y should be always 2 dimensional, but found: X.shape: {X.shape}, y.shape: "
                               f"{y.shape}")
        self.max_size = max_size
        self.new_sw = new_sw  # sample weights
        if weights is None and X is not None:
            self.weights = np.ones(len(self))
        else:
            self.weights = np.array([])

    def __getitem__(self, value: Tuple):
        return Dataset(self.X[value, :], self.y[value, :], max_size=self.max_size,
                       new_sw=self.new_sw, weights=None)

    def __iadd__(self, other):
        for attr in ['X', 'y']:
            old = getattr(self, attr)
            new = getattr(other, attr)
            setattr(self, attr, np.vstack((old.reshape(-1, new.shape[1]), new)))

        # add old and new weights
        old = np.ones_like(self.weights)
        new = np.full(other.weights.shape, self.new_sw)
        self.weights = np.concatenate((old, new))
        return self

    def __iter__(self):
        yield self.X
        yield self.y

    def __len__(self):
        xlen = self.X.shape[0]
        ylen = self.y.shape[0]
        if xlen != ylen:
            raise RuntimeError('Label and Data is not of the same length. Dataset is borked')
        return xlen

    @property
    def is_empty(self):
        return len(self) == 0

    @property
    def xdim(self):
        return self.X.shape[1]

    @property
    def ydim(self):
        return self.y.shape[1]

    @staticmethod
    def prepare(dataset: str, max_input_len=500):
        """ this method takes dataset.zip and loads the data into this class  """
        logger.info("loading dataset")
        dataset = np.load(dataset)

        X, y = [], []
        for inp in dataset.items():
            if 'input' in inp[0]:
                filebytes = inp[1]
                X.append(filebytes + bytes(bytearray(max_input_len - len(filebytes))))
                try:
                    filename = "cov_" + inp[0].split('_')[1]
                    y.append(dataset[filename])
                except KeyError as ke:
                    raise RuntimeError("Problem while loading dataset: can't find related coverage file:", ke)

        yy = np.array([np.frombuffer(c, dtype=np.uint8) for c in y]).astype(np.float64)
        # todo: remember to remove this when coverages use count style (>1.0 also possible)
        yy[yy > 1.0] = 1.0
        return Dataset(X=np.array([np.frombuffer(b, dtype=np.uint8) for b in X]), y=yy)

    def split(self, frac=.8):
        if self.is_empty:
            raise RuntimeError('Can\'t split an empty dataset')

        # returns split to train and validation datasets with given fraction
        x, y = [np.split(k, [int(frac * len(k))]) for k in self]
        return Dataset(x[0], y[0], max_size=self.max_size,
                       new_sw=self.new_sw, weights=None), Dataset(x[1], y[1], max_size=self.max_size,
                                                                  new_sw=self.new_sw, weights=None)
