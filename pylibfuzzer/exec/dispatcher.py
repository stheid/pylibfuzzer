import logging
import os
from os.path import exists
from socket import socket, AF_UNIX, SOCK_STREAM
from struct import unpack, pack
from subprocess import Popen
from typing import List, Tuple

logger = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self, runner, jazzer_cmd, sock_addr, workdir='.', logfile=None):
        self.i = 0
        self.runner = runner
        self.cmd = jazzer_cmd
        self.workdir = workdir
        self.addr = sock_addr
        self.log_file = None
        self.jazzer_log_name = logfile

    def __create_socket(self):
        if self.jazzer_log_name is not None:
            self.log_file = open(self.jazzer_log_name, 'w')
        self.sock = socket(AF_UNIX, SOCK_STREAM, proto=0)
        if exists(self.addr):
            logger.info("Address already exists, removing ... %s", self.addr)
            os.remove(self.addr)
        self.sock.bind(self.addr)
        self.sock.listen(1)
        logger.debug("Created Socket and listening for connection")
        logger.debug("Starting up jazzer...")
        # client connection - jazzer
        self.proc = Popen(self.cmd, cwd=self.workdir, stdout=self.log_file, stderr=self.log_file)
        logger.debug('Accepting connections from Jazzer')
        # accept connection from client
        self.conn, _ = self.sock.accept()

    def __enter__(self):
        logger.info('Starting %s', self.cmd)
        self.__create_socket()
        logger.info("Accepted connection from {:s}".format(self.addr))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.jazzer_log_name is not None:
            self.log_file.close()
        try:
            self.proc.kill()
        except OSError:
            pass
        self.sock.close()
        os.remove(self.addr)

    def post(self, data: bytes) -> Tuple[List[bytes], List[bool]]:
        """
        Posts the byte to the jazzer oracle and returns the oracles results in a synchronous manner

        :param data: The file to test in the oracle
        :return: a list of pairs of Coverages and IsNotCrashed boolean
        """
        pass


class MultiDispatcher(Dispatcher):
    def __init__(self, runner, jazzer_cmd, sock_addr, mut_reps, workdir='.', logfile=None):
        super().__init__(runner=runner, jazzer_cmd=jazzer_cmd, workdir=workdir, sock_addr=sock_addr, logfile=logfile)
        self.mut_reps = mut_reps
        self.return_size = None
        self.empty_coverages_count = 0

    def post(self, data: bytes) -> Tuple[List[bytes], List[bool]]:
        # SEND INPUT
        datalen = len(data)
        # mutation repetitions
        self.conn.sendall(pack('I', self.mut_reps))
        # input length and input
        self.conn.sendall(pack('I', datalen) + data)
        logger.debug('Sent file with %dbytes', datalen)

        # READ FUZZER OBSERVATIONS
        n_coverages = unpack('I', self.conn.recv(4))[0]
        if n_coverages != self.mut_reps + 1:
            logger.debug(
                f'Received {n_coverages} coverages, but requested {self.mut_reps} repetitions plus the generated input')
        cov, succ = [], []
        for i in range(n_coverages):
            len_ = unpack('I', self.conn.recv(4))[0]
            cov.append(self.conn.recv(len_))
            succ.append(unpack('?', self.conn.recv(1))[0])
            logger.debug('Received result of %dbytes', len_)

            if self.return_size is None:
                self.return_size = len(cov[0])

        if len(cov) == 0:
            self.empty_coverages_count += 1
            if self.return_size is not None:
                logger.warning(
                    'return value was emtpy, setting to coverage to 0ed bytes of same length as general return values')
                logger.debug(f'File that caused the zero coverage:\n{data}')
                res = [bytes(bytearray(self.return_size))]
            else:
                raise RuntimeError(f'PuT did not return any measurements in first iteration.\nFile:\n{data}')
        return cov, succ


class InitialMultiDispatcher(Dispatcher):
    def __init__(self, runner, jazzer_cmd, sock_addr, jazzer_iter, workdir='.', logfile=None):
        super().__init__(runner=runner, jazzer_cmd=jazzer_cmd, workdir=workdir, sock_addr=sock_addr, logfile=logfile)
        self.jazzer_iter = jazzer_iter
        self.return_size = None
        self.warmup = True
        self.empty_coverages_count = 0

    def post(self, data: bytes) -> Tuple[List[bytes], List[bool]]:
        # SEND INPUT
        datalen = len(data)
        if self.warmup == True:
            self.warmup = False
            n = self.jazzer_iter
        else:
            n = 0

        # mutation repetitions
        self.sock.sendall(pack('I', n))
        # input length and input
        self.sock.sendall(pack('I', datalen) + data)
        logger.debug('Sent file with %dbytes', datalen)

        # READ FUZZER OBSERVATIONS
        n_coverages = unpack('I', self.sock.recv(4))[0]
        cov, succ = [], []
        for i in range(n_coverages):
            len_ = unpack('I', self.sock.recv(4))[0]
            cov.append(self.conn.recv(len_))
            succ.append(unpack('?', self.conn.recv(1))[0])
            logger.debug('Received result of %dbytes', len_)
            if self.return_size is None:
                self.return_size = len(cov[0])

        if len(cov) == 0:
            self.empty_coverages_count += 1
            if self.return_size is not None:
                logger.warning(
                    'return value was emtpy, setting to coverage to 0ed bytes of same length as general return values')
                logger.debug(f'File that caused the zero coverage:\n{data}')
                res = [bytes(bytearray(self.return_size))]
            else:
                raise RuntimeError(f'PuT did not return any measurements in first iteration.\nFile:\n{data}')
        return cov, succ
