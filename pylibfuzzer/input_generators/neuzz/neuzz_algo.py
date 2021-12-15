from typing import List, Tuple
import logging
import numpy as np
from tqdm import tqdm, trange

from pylibfuzzer.input_generators.base import BaseFuzzer
from pylibfuzzer.input_generators.neuzz.model import NeuzzModel

logger = logging.getLogger(__name__)


class Dataset:
    def __init__(self, X: np.array = None, y: np.array = None,
                 max_size=10000, new_sw=2, weights=None):
        self.X = np.array([]) if X is None else X
        self.y = np.array([]) if y is None else y
        self.max_size = max_size
        self.new_sw = new_sw  # sample weights
        if weights is None and X is not None:
            self.weights = np.ones(len(self))
        else:
            self.weights = np.array([])

    #
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

    def split(self, frac=.8):
        if self.is_empty:
            raise RuntimeError('Can\'t split an empty dataset')

        # returns split to train and validation datasets with given fraction
        x, y = [np.split(k, [int(frac * len(k))]) for k in self]
        return Dataset(x[0], y[0], max_size=self.max_size,
                       new_sw=self.new_sw, weights=None), Dataset(x[1], y[1], max_size=self.max_size,
                                                                  new_sw=self.new_sw, weights=None)


class NeuzzFuzzer(BaseFuzzer):
    """
    This class implements the Neuzz algorithm.
    """

    def __init__(self, jazzer_cmd, initial_dataset_len, max_input_len=500, n_mutation_candidates=10,
                 n_mutation_positions=100, exp=6, network=[512], epochs=10):
        super().__init__()
        self.exp = exp
        self.batch = None
        self.model = NeuzzModel(epochs=epochs)
        self._do_warmup = True
        self.cmd = jazzer_cmd
        self.network = network
        self.network = network
        self.max_input_len = max_input_len
        self.initial_dataset_len = initial_dataset_len
        self.n_mutation_candidates = n_mutation_candidates
        self.n_mutation_positions = n_mutation_positions
        self.covered_edges = set()

        # uint8, float32, samples×width
        self.train_data = Dataset()
        self.val_data = Dataset()

    def create_inputs(self) -> List[bytes]:
        """
        - uses jazzer to create (input,output),
        - trains model using these input
        :return:
        """
        if self._do_warmup:
            ## LATER
            # [optional] collect seedfiles if any
            # run jazzer with the seedfiles
            # run jazzer for a defined time to collect training data -> (input,cov)
            # self._retrain(listOf())

            ## V0
            # generate 10k random inputs
            batch = []
            for i in trange(self.initial_dataset_len):
                batch.append(np.random.bytes(self.max_input_len))
            # create random data -> in observe we will train the model for the first iteration
            self._do_warmup = False
        else:
            batch = self._generateInputs()

        self.batch = batch
        return self.batch

    def observe(self, fuzzing_result: List[np.ndarray]):

        data = Dataset(np.array([np.frombuffer(b, dtype=np.uint8) for b in self.batch]),
                       np.array(fuzzing_result).squeeze())

        not_yet_covered_edges = np.ones(data.ydim)
        not_yet_covered_edges[list(self.covered_edges)] = 0
        new_data_view = data.y[:, not_yet_covered_edges.astype(bool)]
        self.covered_edges = self.covered_edges.union(set(np.nonzero(new_data_view.sum(axis=0))[0]))
        candidate_indices = np.nonzero(new_data_view.sum(axis=1))[0]

        # select only covered edges from indices calculated above
        new_data = data[candidate_indices]

        # if there is no data then no need for training again
        if new_data.is_empty:
            logger.info("dataset empty")
            return

        # split
        train_data, val_data = new_data.split(frac=0.8)

        # Initialize model and update train and val data for training
        if self.model.is_model_created:
            self.train_data += train_data
            self.val_data += val_data
        else:
            self.model.initialize_model(train_data.xdim, train_data.ydim, network=self.network)
            self.train_data = train_data
            self.val_data = val_data

        # train NN
        self._retrain()

    def _retrain(self):
        """
        Retrain model with additional training data
        :param: new data is stored in self.train_data and self.val_data
        """

        # pass old and new data separately along with weights
        self.model.train(self.train_data, self.val_data)

    @staticmethod
    def gen_mutations(candidate, grad, exp=6) -> List[np.array]:
        candidate = candidate.squeeze()
        grad = grad.squeeze()
        successors = []

        # k largest indices
        locs = np.argpartition(np.abs(grad), 2 ** exp)[-2 ** exp:].squeeze()

        for loc in locs:
            for m in range(1, 256):
                new = candidate.copy()
                v = candidate[loc] + m * np.sign(grad[loc])
                if v == np.clip(v, 0, 255):
                    new[loc] = v
                    successors.append(new)
                else:
                    break
        return successors

    def _generateInputs(self) -> List[bytes]:
        # select collection of parent files
        mask = np.random.choice(len(self.train_data), self.n_mutation_candidates, replace=False)
        candidates = self.train_data.X[mask]
        candidate_labels = self.train_data.y[mask]

        # enable additional coverage bits in the output

        results = []
        for x, y in zip(tqdm(candidates), candidate_labels):
            # set some "close to zero"-values to one (means we enable some additional coverage markers)
            zero_idxs = np.where(y == 0)[0]
            new_ones = np.random.choice(zero_idxs, self.n_mutation_positions, replace=False)
            y[new_ones] = 1

            # backpropagation to the input and get the gradients [Keras]
            gradient = self.model.gradient(x, y)
            # print(gradient)

            # generate new mutated inputs using the gradient and exhaustive search (Algo 1 from the paper)
            mutations = NeuzzFuzzer.gen_mutations(x, gradient, exp=self.exp)
            bytes_mutations = [x.tobytes() for x in mutations]
            results.extend(bytes_mutations)

        return results
