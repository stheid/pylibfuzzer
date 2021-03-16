class BaseFuzzer:
    def __init__(self):
        pass

    def load_seed(self, path):
        """
        loads all files in the seed to the model

        :param path:
        :return:
        """
        pass

    def create_input(self) -> list[bytes]:
        """
        create new input from internal model

        in most implementations the first couple of inputs from this functions will be the seed files
        :return: list of files as bytes
        """
        pass

    def observe(self, fuzzing_result: list[bytes]):
        """
        gets execution results of the last input batch passed to the PUT.

        :param fuzzing_result:
        :return:
        """
        pass
