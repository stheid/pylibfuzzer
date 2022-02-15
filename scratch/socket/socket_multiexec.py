import hashlib
from datetime import datetime
from socket import socket, AF_UNIX, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, error
from struct import unpack, pack
from subprocess import Popen
from time import sleep
from typing import Generator, Iterable
from sys import stdout
import click
import numpy as np


def server(input_):
    return hashlib.sha224(input_).digest()


def client() -> Iterable[bytes]:
    while True:
        yield np.random.bytes(10)


def post_inputs(input_, conn):
    # SEND INPUT
    datalen = len(input_)
    # print(datalen)
    # mutation repetions
    # print("sending")
    # sock.send(b'5')
    # conn.send(pack('I', 0))
    conn.sendall(pack('I', 0))  # no mutreps
    # print("sent")
    # input length and input
    conn.sendall(pack('I', datalen) + input_)
    # print('SENT>> ' + str(input_))

    # READ FUZZER OBSERVATIONS
    n_coverages = unpack('I', conn.recv(4))[0]
    for i in range(n_coverages):
        len_ = unpack('I', conn.recv(4))[0]
        res = conn.recv(len_)
        # print('RECV>> ' + str(res))


# in jazzer
def receiving_inputs(sock):
    mutrep = unpack('I', sock.recv(4))[0]
    len_ = unpack('I', sock.recv(4))[0]
    input_ = sock.recv(len_)
    # print('RECV>> ' + str(input_))
    out = mutrep + 1
    sock.sendall(pack('I', out))
    for i in range(out):
        result = server(input_)
        sock.sendall(pack('I', len(result)) + result)
        # print('SENT>> ' + str(result))

    return input_


@click.command()
@click.option('--role', default='server', help='Server or client role?')
@click.option('--addr', default='/tmp/test.sock', help='socket address')
def main(role='server', addr='/tmp/test.sock'):
    if role == 'server':
        sock = socket(AF_UNIX, SOCK_STREAM, proto=0)
        # sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.bind(addr)
        sock.listen(1)
        Popen(['../../bin/jazzer/jazzer', '-oracle=1', '--keep-going=100000', '--cp=examples_deploy.jar',
               '--target_class=com.example.JsonSanitizerDenylistFuzzer'], stdout=stdout, stderr=stdout)
        # sleep(1)
        conn, client_address = sock.accept()
        print("Accepted connection from {:s}".format(client_address))
        for input_ in client():
            post_inputs(input_, conn)

        sock.close()
    else:

        with socket(AF_UNIX, SOCK_STREAM, proto=0) as sock:
            start = datetime.now()
            while True:
                try:
                    sock.connect(addr)
                    # print("connection established")
                    break
                except (ConnectionRefusedError, FileNotFoundError):
                    # wait and retry
                    # print(f'Waiting for {addr} to accept connections ({(datetime.now() - start).seconds:.1f}s)',
                    #       end='\r')
                    sleep(.1)

            while receiving_inputs(sock):
                pass


if __name__ == '__main__':
    main()
