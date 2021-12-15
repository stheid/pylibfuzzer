from typing import List


class BaseDispatcher:
    interfacetype = None

    def __init__(self, runner, jazzer_cmd):
        self.runner = runner
        self.cmd = jazzer_cmd

    def post(self, data: bytes) -> List[bytes]:
        pass
