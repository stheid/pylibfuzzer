from pylibfuzzer.obs_extraction.base import BaseExtractor, CovVectorMixin


class PcVectorExtractor(BaseExtractor, CovVectorMixin):
    def extract_obs(self, b: bytes) -> set:
        """

        :param b:
        :return: observation similar to openAI gym
        """
        return self.to_coverage_vec_and_record(b)
