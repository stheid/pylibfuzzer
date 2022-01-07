from typing import List
import logging
import numpy as np
from tqdm import tqdm, trange

from pylibfuzzer.input_generators.base import BaseFuzzer
from .dataset import Dataset
from .model import NeuzzModel

logger = logging.getLogger(__name__)


class NeuzzFuzzer(BaseFuzzer):
    """
    This class implements the Neuzz algorithm.
    """

    def __init__(self, jazzer_cmd, initial_dataset_len, max_input_len=500, n_mutation_candidates=10,
                 n_mutation_positions=100, exp=6, network=(512,), epochs=10):
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
            # self.model.train(self.train_data, self.val_data)

            ## V0
            # generate 10k random inputs
            batch = []
            for i in trange(self.initial_dataset_len):
                batch.append(np.random.bytes(self.max_input_len))
            # create random data -> in observe we will train the model for the first iteration
            self._do_warmup = False
        else:
            batch = self._generate_inputs()

        self.batch = batch
        return self.batch

    def observe(self, fuzzing_result: List[np.ndarray]):
        data = Dataset(np.array([np.frombuffer(b, dtype=np.uint8) for b in self.batch]),
                       np.array(fuzzing_result).squeeze())

        # updating covered edges and prepare a mask to filter the dataset on covered edges
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
        self.model.train(self.train_data, self.val_data)

    @staticmethod
    def _gen_mutations(candidate, grad, exp=6) -> List[np.array]:
        candidate = candidate.squeeze()
        grad = grad.squeeze()
        successors = []

        # k^exp largest indices with k=2
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

    def _generate_inputs(self) -> List[bytes]:
        # select collection of parent files
        mask = np.random.choice(len(self.train_data), self.n_mutation_candidates, replace=False)
        candidates = self.train_data.X[mask]
        candidate_labels = self.train_data.y[mask]

        inputs = []
        for x, y in zip(tqdm(candidates), candidate_labels):
            # enable additional coverage bits in the output
            # set some "close to zero"-values to one (means we enable some additional coverage markers)
            zero_idxs = np.where(y == 0)[0]
            new_ones = np.random.choice(zero_idxs, self.n_mutation_positions, replace=False)
            y[new_ones] = 1

            # backpropagation to the input and get the gradients [Keras]
            gradient = self.model.gradient(x, y)

            # generate new mutated inputs using the gradient and exhaustive search (Algo 1 from the paper)
            mutations = NeuzzFuzzer._gen_mutations(x, gradient, exp=self.exp)
            bytes_mutations = [x.tobytes() for x in mutations]
            inputs.extend(bytes_mutations)

        return inputs
