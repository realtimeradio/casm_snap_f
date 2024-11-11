#! /usr/bin/env python

import time
import socket
import struct
import numpy as np

HEADER_LEN = 16
RECV_BYTES = 8192 + HEADER_LEN

def decode_packet(p):
    t, c, f, nc, npl = struct.unpack('>QHHHH', p[0:HEADER_LEN])
    data = np.frombuffer(p[HEADER_LEN:], dtype='>u1')
    return t, c, f, nc, npl, data

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 10000))

pcnt = 0

while(True):
    try:
        p = sock.recv(RECV_BYTES)
        t, c, f, nc, npl, data = decode_packet(p)
        print(f'TIME {t}, CHAN {c}; FID {f}; NC {nc}; NP {npl}; data0,1,2,3 {data[0:4]}')
        pcnt += 1
    except KeyboardInterrupt:
        break

sock.close()
