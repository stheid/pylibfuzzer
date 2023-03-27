from typing import List

import numpy as np

from pylibfuzzer.input_generators.base import BaseFuzzer
from pylibfuzzer.input_generators.transformer.model import TransformerModel


class TransformerFuzzer(BaseFuzzer):
    """
    This class implements a fuzzer using Transformer
    """

    def __init__(self, dataset=None):
        super().__init__()
        self.n_mutation_positions = None
        self.dataset = dataset
        self.batch = []
        self.model = TransformerModel()

        self.n_mutation_candidates = None
        self.train_data = None

    def prepare(self):
        pass

    def load_seed(self, seedfiles):
        pass

    def create_inputs(self) -> List[bytes]:
        pass

    def observe(self, fuzzing_result: List[bytes]):
        pass

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
