import logging
from socket import socket, AF_UNIX, SOCK_STREAM
from struct import unpack, pack
from subprocess import Popen, DEVNULL
from time import sleep

logger = logging.getLogger(__name__)


class SocketDispatcher:
    def __init__(self, runner, cmd, addr):
        self.i = 0
        self.runner = runner
        self.cmd = cmd
        self.addr = addr

    def __enter__(self):
        logger.info('Starting %s', self.cmd)
        self.proc = Popen(self.cmd, stdout=DEVNULL, stderr=DEVNULL)
        self.sock = socket(AF_UNIX, SOCK_STREAM)
        self.sock.__enter__()
        while True:
            try:
                self.sock.connect(self.addr)
                logger.info('Starting Fuzzing')
                return self
            except ConnectionRefusedError:
                # wait and retry
                sleep(.1)
            except FileNotFoundError:
                print('Server (libfuzzer) not yet started. Retrying in 1s...')
                sleep(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.sock.__exit__(exc_type, exc_val, exc_tb)

    def post(self, data: bytes) -> bytes:

        datalen = len(data)
        self.sock.sendall(pack('I', datalen) + data)
        logger.debug('Sent file with %dbytes', datalen)
        # logger.debug(data)

        len_ = unpack('I', self.sock.recv(4))[0]
        res = self.sock.recv(len_)
        logger.debug('Recieved result of %dbytes', len_)
        logger.debug(res)
        return res
