import logging
from socket import socket, AF_UNIX, SOCK_STREAM
from struct import unpack, pack
from subprocess import Popen

logger = logging.getLogger(__name__)


class SocketDispatcher:
    def __init__(self, runner, cmd, addr):
        self.runner = runner
        self.cmd = cmd
        self.addr = addr

    def __enter__(self):
        self.proc = Popen(self.cmd)
        self.sock = socket(AF_UNIX, SOCK_STREAM)
        self.sock.__enter__()
        self.sock.connect(self.addr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.sock.__exit__(exc_type, exc_val, exc_tb)

    def post(self, data: bytes) -> bytes:
        datalen = len(data)
        self.sock.sendall(pack('I', datalen) + data)
        logger.info('Sent file with {d}bytes', datalen)

        len_ = unpack('I', self.sock.recv(4))[0]
        logger.info('Recieved result of {d}bytes', len_)
        return self.sock.recv(len_)
