#! /usr/bin/env python

import time
import socket
import struct
import numpy as np

HEADER_LEN = 16
RECV_BYTES = 8192 + HEADER_LEN
FS = 250e6 # Sample rate in Hz
NFFT = 8192 # FFT size (=2 x number of channels)

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
        ctime = time.ctime(NFFT * t / FS)
        print(f'TIME {t} ({ctime}), CHAN {c}; FID {f}; NC {nc}; NP {npl}; data0,1,2,3 {data[0:4]}')
        pcnt += 1
    except KeyboardInterrupt:
        break

sock.close()
