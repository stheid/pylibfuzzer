class BaseFuzzer:
    supported_extractors = []

    def __init__(self):
        self._initialized = False

    def load_seed(self, path):
        # extract parse tree of all inputs / alternatively start of with a random set of trees
        pass

    def create_inputs(self) -> List[bytes]:
        # generate offsprings of the population via mutation/crossover
        # return offsprings
        return []

    def observe(self, fuzzing_result: List[bytes]):
        # observe coverages
        # update the fitness function (icfg model)
        # calculate performance of the whole population
        # kill all individuals that are not among the n best performing
        pass
