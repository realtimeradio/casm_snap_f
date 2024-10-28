import logging
from .. import helpers
from ..error_levels import *
from .block import Block

class Adc(Block):
    """
    Instantiate a control interface for an ADC block.

    :param host: CasperFpga interface for host.
    :type host: casperfpga.CasperFpga

    :param name: Name of block in Simulink hierarchy.
    :type name: str

    :param sample_rate_mhz: Target sample rate in MHz
    :type sample_rate_mhz: float

    :param logger: Logger instance to which log messages should be emitted.
    :type logger: logging.Logger
    """

    def __init__(self, host, name, logger=None, sample_rate_mhz=250.):
        super(Adc, self).__init__(host, name, logger)
        self.adc = None
        self.sample_rate_mhz = sample_rate_mhz
    def initialize(self, read_only=False):
        """
        Initialize the block.

        :param read_only: If True, do nothing. If False, configure the ADC.
        :type read_only: bool

        """
        if read_only:
            pass
        else:
            try:
                self.adc = self.host.adcs[self.prefix + 'snap_adc']
            except AttributeError:
                self._error("Failed to find ADC. Have you provided an FPG file?")
                raise RuntimeError
            self._info("Training ADC link")
            err = self.adc.init(sample_rate=self.sample_rate_mhz, numChannel=4, verify=True)
            self._info(f"Link training returned {err}")
            if err != self.adc.SUCCESS:
                raise RuntimeError(f"ADC initialization failed with code {err}")
