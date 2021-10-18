from pylibfuzzer.obs_transform.pipeline import Transformer, CovSet, Reward


class SimpleRewardTransformer(Transformer):
    def __init__(self, offset=100):
        super().__init__()
        self.iteration = 0
        self.iter_of_first_cov = dict()
        self.offset = offset

    def __call__(self, data: CovSet) -> Reward:
        """
        :param data:
        :return:
        """
        self.iteration += 1
        reward = 0
        for marker in data:
            # iterations elapsed since the coverage marker has been descovered
            elapsed_iters = self.iteration - self.iter_of_first_cov.setdefault(marker, self.iteration)
            # recent coverages yield higher reward
            reward += 1 / (1 + self.offset + elapsed_iters)
        return reward
