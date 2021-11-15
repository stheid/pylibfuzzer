from typing import List


class BaseDispatcher:
    interfacetype = None

    def post(self, data: bytes) -> List[bytes]:
        pass
