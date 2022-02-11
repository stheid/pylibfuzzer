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


def post_inputs(input_, sock):
    # SEND INPUT
    datalen = len(input_)
    print(datalen)
    # mutation repetions
    print("sending")
    # sock.send(b'5')
    sock.sendall(pack('I', 0))  # no mutreps
    print("sent")
    # input length and input
    sock.sendall(pack('I', datalen) + input_)
    print('SENT>> ' + str(input_))

    # READ FUZZER OBSERVATIONS
    n_coverages = unpack('I', sock.recv(4))[0]
    for i in range(n_coverages):
        len_ = unpack('I', sock.recv(4))[0]
        res = sock.recv(len_)
        print('RECV>> ' + str(res))


# in jazzer
def receiving_inputs(conn):
    mutrep = unpack('I', conn.recv(4))[0]
    len_ = unpack('I', conn.recv(4))[0]
    input_ = conn.recv(len_)
    print('RECV>> ' + str(input_))
    out = mutrep + 2
    conn.sendall(pack('I', out))
    for i in range(0, out):
        result = server(input_)
        conn.sendall(pack('I', len(result)) + result)
        print('SENT>> ' + str(result))

    return input_


@click.command()
@click.option('--role', default='server', help='Server or client role?')
@click.option('--addr', default='/tmp/test.sock', help='socket address')
def main(role='server', addr='/tmp/test.sock'):
    if role == 'server':
        with socket(AF_UNIX, SOCK_STREAM, proto=0) as sock:
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            try:
                sock.bind(addr)
                sock.listen(1)
                while True:
                    conn, client_address = sock.accept()
                    print("Accepted connection from {:s}".format(client_address))
                    for input_ in client():
                        post_inputs(input_, sock)
            except AttributeError as ae:
                print("Error creating the socket: {}".format(ae))
            except error as se:
                print("Exception on socket: {}".format(se))
            except KeyboardInterrupt:
                sock.close()
            finally:
                print("Closing socket")
                sock.close()

    else:
        # Popen(['../../bin/jazzer/jazzer', '-oracle=1', '--keep-going=100000', '--cp=examples_deploy.jar',
        #        '--target_class=com.example.JsonSanitizerDenylistFuzzer'], stdout=stdout, stderr=stdout)
        # sleep(1)
        with socket(AF_UNIX, SOCK_STREAM, proto=0) as sock:
            start = datetime.now()
            while True:
                try:
                    sock.connect(addr)
                    print("connection established")
                    break
                except (ConnectionRefusedError, FileNotFoundError):
                    # wait and retry
                    print(f'Waiting for {addr} to accept connections ({(datetime.now() - start).seconds:.1f}s)',
                          end='\r')
                    sleep(.1)

            while receiving_inputs(sock):
                pass


if __name__ == '__main__':
    main()
