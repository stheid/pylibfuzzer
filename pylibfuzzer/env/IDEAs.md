# General

implement fuzztarget as a openAIgym

# step()

step will return always an dictionary and an reward as integer. The dictionary will be a key and than the fuzztarget
result. This key will represent the type of data returned. This allows to program einvs that return several types of
input data to be used by the fuzzing algorithms. We could than specify the datatypes that each fuzzingalgo supports (as
a list in the class variable) and than validate that env and algorithm fit together

the alphafuzz algo for example needs a reward and the coverage in form of a dense vector over all program counters.

# changes to implement

- This change will remove the fitness module or make it part of the environment module.
- algos:
    - each algo class gets a "execpted observation type" class variable
    - the observe function will get two parameters: states, rewards. batch wise execution will therefore still be
      allowed, however might implement a dummy "batchobserve" function that will take care of simple sequential
      observation handling which is the case for all currently implemented algorithms
      https://docs.python.org/3/library/functools.html#functools.singledispatchmethod