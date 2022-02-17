from typing import List


class BaseDispatcher:
    interfacetype = None

    def __init__(self, runner, jazzer_cmd, workdir):
        self.runner = runner
        self.cmd = jazzer_cmd
        self.workdir = workdir

    def post(self, data: bytes) -> List[bytes]:
        pass
