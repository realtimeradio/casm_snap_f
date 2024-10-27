import logging
import numpy as np
import struct
import socket
import time
import progressbar
import casperfpga
from .. import helpers
from ..error_levels import *
from .block import Block

TAP_STEP_SIZE = 8
NSAMPLES = 256
NBOARDS = 2
NFMCS = 2

CONTROL_REG = 'sync'

RST_BIT = 0
EXT_SS_TRIG_EN_BIT = 1
SS_TRIG_BIT = 2
EXT_SYNC_EN_BIT = 3
SYNC_BIT = 4

class Adc(Block):
    """
    Instantiate a control interface for an ADC block.

    :param host: CasperFpga interface for host.
    :type host: casperfpga.CasperFpga

    :param name: Name of block in Simulink hierarchy.
    :type name: str

    :param logger: Logger instance to which log messages should be emitted.
    :type logger: logging.Logger
    """

    def __init__(self, host, name, logger=None, passive=False):
        super(Adc, self).__init__(host, name, logger)
        # Check which ADCs are connected. Only if no ADC chips on an FMC board
        # respond do we ignore a port
        self.adcs = []
