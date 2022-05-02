# from typing import List
# import logging
# import numpy as np
# from tqdm import trange, tqdm
#
# from pylibfuzzer.util.dataset import Dataset, DatasetIO
# from .model import NeuzzModel
# from pylibfuzzer.input_generators.base import BaseFuzzer
# from .. import NeuzzFuzzer
# from ...util.array import remove_lsb
#
# logger = logging.getLogger(__name__)
#
# class NeuzzDirectedFuzzer(BaseFuzzer):
#
#     def __init__(self, jazzer_cmd, initial_dataset_len, cfg, dataset=None, max_input_len=500, n_mutation_candidates=10,
#                  n_mutation_positions=100, exp=6, network=(512,), epochs=10):
#         super().__init__()
#         self.cfg = cfg
#         self.exp = exp
#         self.batch = []
#         self.model = NeuzzModel(epochs=epochs)
#         self._do_warmup = True
#         self.cmd = jazzer_cmd
#         self.network = network
#         self.max_input_len = max_input_len
#         self.initial_dataset_len = initial_dataset_len
#         self.n_mutation_candidates = n_mutation_candidates
#         self.n_mutation_positions = n_mutation_positions
#         self.uncovered_bits = None
#         self.dataset = dataset
#
#         # uint8, float32, samples×width
#         self.train_data = Dataset()
#         self.val_data = Dataset()
#
#     def prepare(self):
#         """ load already given dataset and pre-train model once."""
#         if self.dataset is not None:
#             self.train_data, self.val_data = \
#                 DatasetIO.load(dataset_path=self.dataset, max_input_len=self.max_input_len).split()
#             # Initialize model and update train and val data for training
#             if not self.model.is_model_created:
#                 self.model.initialize_model(self.train_data.xdim, self.train_data.ydim, network=self.network)
#
#             # train NN
#             logger.info("Begin training on pre-given dataset")
#             self.model.train(self.train_data, self.val_data)
#             logger.info("Finished training on pre-given dataset")
#
#             self._do_warmup = False
#
#     def load_seed(self, seedfiles):
#         for file in seedfiles:
#             with open(file, 'rb') as f:
#                 input = f.read()
#             # cut and pad seedfiles to be exact self.max_input_length
#             input = input[:self.max_input_len] + bytes(bytearray(max(0, self.max_input_len - len(input))))
#             self.batch.append(input)
#
#     def create_inputs(self) -> List[bytes]:
#         """
#         - uses jazzer to create (input,output),
#         - trains model using these input
#         :return:
#         """
#         if self._do_warmup:
#             self._do_warmup = False
#
#             batch = self.batch
#             # fill up with random inputs to match desired size
#             for _ in trange(len(batch), self.initial_dataset_len):
#                 file_len = np.random.randint(self.max_input_len)
#                 batch.append(np.random.bytes(file_len) + bytes(bytearray(self.max_input_len - file_len)))
#         else:
#             batch = self._generate_inputs()
#
#         self.batch = batch
#         return self.batch
#
#     def observe(self, fuzzing_result: List[np.ndarray]):
#         data = Dataset(np.array([np.frombuffer(b, dtype=np.uint8) for b in self.batch]),
#                        np.array(fuzzing_result))
#
#         if self.uncovered_bits is None:
#             self.uncovered_bits = np.ones_like(fuzzing_result[0], dtype=np.uint8)
#
#         candidate_indices = []
#         for i, result in enumerate(fuzzing_result):
#             rmsb = remove_lsb(result)
#
#             if np.any(rmsb & self.uncovered_bits):
#                 self.uncovered_bits &= ~rmsb
#                 candidate_indices.append(i)
#
#         # select only covered edges from indices calculated above
#         new_data = data[tuple(candidate_indices)]
#
#         # if there is no data then no need for training again
#         if new_data.is_empty:
#             logger.info("No newly covered edges: all inputs discarded.")
#             return
#
#         # split
#         train_data, val_data = new_data.split(frac=0.8)
#
#         # Initialize model and update train and val data for training
#         if self.model.is_model_created:
#             self.train_data += train_data
#             self.val_data += val_data
#         else:
#             self.model.initialize_model(train_data.xdim, train_data.ydim, network=self.network)
#             self.train_data = train_data
#             self.val_data = val_data
#
#         # train NN
#         self.model.train(self.train_data, self.val_data)
#
#     def _generate_inputs(self) -> List[bytes]:
#         # select collection of parent files
#         mask = np.random.choice(len(self.train_data), self.n_mutation_candidates, replace=False)
#         candidates = self.train_data.X[mask]
#         candidate_labels = self.train_data.y[mask]
#
#         inputs = []
#         for x, y in zip(tqdm(candidates), candidate_labels):
#             # enable additional coverage bits in the output
#             # set some "close to zero"-values to one (means we enable some additional coverage markers)
#             zero_idxs = np.where(y == 0)[0]
#             new_ones = np.random.choice(zero_idxs, self.n_mutation_positions, replace=False)
#             y[new_ones] = 1
#
#             # backpropagation to the input and get the gradients [Keras]
#             gradient = self.model.gradient(x, y)
#
#             # generate new mutated inputs using the gradient and exhaustive search (Algo 1 from the paper)
#             mutations = NeuzzFuzzer._gen_mutations(x, gradient, exp=self.exp)
#             bytes_mutations = [x.tobytes() for x in mutations]
#             inputs.extend(bytes_mutations)
#
#         return inputs
#
# def find_pre(cfg, target, v, T):
#     """ Auxiliary Functions : functions that return the node(s) in the CFG that is/are v steps before target"""
#     if v > 0:
#         return cfg(target, v, T)
#     return target
#
#
# # nodes,v steps before target and on a possible path
# # target = T[i]
#
#
# def select_func(self, target, N, k):  # return list of next=(x*,y*) i.e. elements of N
#     """ function that returns the (input,coverage) pairs of N, subset of S, that should be used using Neuzz next"""
#     next = []
#     v = 0
#     p = 0
#
#     while v < k:
#         pre = find_pre(self.cfg, target, v)
#         # list of node(s) in CFG that is/are v steps before target on a possible path
#         for pr in pre:
#             for (x, y) in N:
#                 if y[pr] == 1:
#                     next.append((x, y))
#                     p = 1
#         if p:
#             return next
#         else:
#             v += 1
#
#
# def total_coverage(S):  # return c, NV
#     """Calculation of the total coverage c,
#     vector consists of 1's and 0's with the length of the number of nodes in the CFG
#     c[i] = 1 means that there exists an input in S, or the updates version of S, passing through node i in the CFG
#     c[i] = 0 means that there is no input in S, or the updates version of S, passing through node i in the CFG
#     """
#     c = []
#     NV = [0:k + 1]  # nodes that are not visited yet
#     for (x, y) in S:
#         for i in NM:
#             if y[i] == 1:
#                 c[i] = 1
#                 NV = NV - {i}  # delete i in NM, since i is visited
#
#     return c, NV
#
#
# def Neuzz(candidates):  # return B
#     """ Using of Neuzz to obtain a set containing new (input,coverage)-pairs """
#     # uses Neuzz by using candidates and returns B, the set generated set of (input,coverage)-pairs
#     pass
#
#
#
# def update_A(A, B):
#     """ update A so that a set B, that contains new (input,coverage)-pairs, is included """
#     A[0] = A[0] U B	 #
#     for i in [0:|A|]:
#         for (x,y) in B:
#             if A[i] is not empty:
#                 if y[T[i]]:
#                     A[i+1] U= (x,y)
#             else return A
#
#
# def filter(Neuzzgen, c, NV): # return B, c, NV
#     """function that filters the set nx, that contains (input,coverage)-pairs generated by using Neuzz, in the way that
#         only (input,coverage)-pairs with new coverage are considered
#         S, seed pool and c total coverage vector
#     """
#     B = []
#     for x,y in Neuzzgen:
#         for i in NV:
#             if y[i]:
#                 B.append(x,y)
#                 c[i] = 1
#                 NV = NV - {i}	#delete i in NM, since i is visited
#
#
# def Neuzz_directed(T, S):  # returns set of (x*,y*)'s
#     """ function that tries to find (input,coverage)-pair(s) that pass through all target nodes of T by using Neuzz """
#     c, NV = total_coverage(S)
#
#     # A = A[0],...,A[t], where A[0] seed pool S and A[1],...,A[t] are those subsets of S containing inputs that pass through one or more target nodes
#     A = [[S], ..., []]  # note that |A| = t+1
#
#     for i in range(len(A)):
#         for (x, y) in A[i]:
#             if A[i] is not empty:
#                 if y[T[i]] == 1:  # AK: if this input has coverage, then add it to next entry in A. Since A is a set, there will not be any duplicates.
#                     A[i + 1] U= (x, y)  # adding (x,y) to the next A[], without duplicates
#             else return A
#
#     if A[t] is not empty:
#         return A[t] and write that all those inputs pass through all target nodes of T
#     else
#         while A[t] empty or time limit is reached:
#             for i in range(1, t + 1):
#                 while A[t - i] is not empty or time limit is reached:
#                     candidates = select_func(T[t - i], A[t - i], k)  # list of (input,coverage)-pairs
#                     nx = Neuzz(candidates)  # (input,coverage)-pairs, generated by using candidates
#                     B, c, NV = filter(nx, c, NV)  # filtered (input,coverage)-pairs, updating c and NV
#                     A = update_A(A, B)
#                     delete
#                     candidates in A[0], ..., A[t - i]
