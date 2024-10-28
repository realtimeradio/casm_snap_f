import numpy as np

from .block import Block
from ..error_levels import *

class Pfb(Block):
    _N_CORES = 4 #: Number of FFT sub-cores per PFB block
    SHIFT_MASK = 0b0000000000000 # The stages hard coded in the FFT
    SHIFT_VAL  = 0b0000000000000 # The hard coded shift settings
    DEFAULT_SHIFT = 0b1111011011111
    STAGES = 13
    def __init__(self, host, name, logger=None):
        super(Pfb, self).__init__(host, name, logger)
        self.SHIFT_OFFSET = 0
        self.SHIFT_WIDTH  = 16
        self.STAT_RST_BIT = 18

    def set_fft_shift(self, shift):
        """
        Set the FFT shift schedule.

        :param shift: Shift schedule to be applied.
        :type shift: int
        """
        shift = shift & (2**self.STAGES - 1)
        if shift & self.SHIFT_MASK != self.SHIFT_VAL:
            shift = (self.SHIFT_VAL + (shift & ~self.SHIFT_MASK)) & (2**self.STAGES - 1)
            self._warning("Firmware implements some hardcoded shift stages." 
                          " Setting shift to 0x%x" % shift)
        self.change_reg_bits('ctrl', shift, self.SHIFT_OFFSET, self.SHIFT_WIDTH)

    def get_fft_shift(self):
        """
        Get the currently applied FFT shift schedule. The returned value
        takes into account any hardcoding of the shift settings by firmware.

        :return: Shift schedule
        :rtype: int
        """
        shift = self.get_reg_bits('ctrl', self.SHIFT_OFFSET, self.SHIFT_WIDTH)
        if shift & self.SHIFT_MASK != self.SHIFT_VAL:
            shift = (self.SHIFT_VAL + (shift & ~self.SHIFT_MASK)) & (2**self.STAGES - 1)
            self._warning("Shift register is being overridden by firmware.")
        return shift

    def rst_stats(self):
        """
        Reset overflow event counters.
        """
        self.change_reg_bits('ctrl', 1, self.STAT_RST_BIT)
        self.change_reg_bits('ctrl', 0, self.STAT_RST_BIT)

    def get_overflow_count(self):
        """
        Get the total number of FFT overflow events, since the last
        statistics reset.

        :return: Number of overflows
        :rtype: int
        """
        return self.read_uint("status")

    def get_status(self):
        """
        Get status and error flag dictionaries.

        Status keys:

            - overflow_count (int) : Number of FFT overflow events since last
              statistics reset. Any non-zero value is flagged with "WARNING".

            - fft_shift (str) : Currently loaded FFT shift schedule, formatted
              as a binary string, prefixed with "0b".

        :return: (status_dict, flags_dict) tuple. `status_dict` is a dictionary of
            status key-value pairs. flags_dict is
            a dictionary with all, or a sub-set, of the keys in `status_dict`. The values
            held in this dictionary are as defined in `error_levels.py` and indicate
            that values in the status dictionary are outside normal ranges.

        """

        stats = {}
        flags = {}
        stats['overflow_count'] = self.get_overflow_count()
        if stats['overflow_count'] != 0:
            flags['overflow_count'] = FENG_WARNING
        fft_shift = self.get_fft_shift()
        stats['fft_shift'] = '0b%s' % np.binary_repr(fft_shift, width=self.STAGES)
        return stats, flags
        
    def initialize(self, read_only=False):
        """
        :param read_only: If False, enable the PFB FIR, set the
            FFT shift to the default value, and
            reset the overflow count. If True, do nothing.
        :type read_only: bool
        """
        if read_only:
            return
        self.write_int('ctrl', 0)
        self.set_fft_shift(self.DEFAULT_SHIFT)
        self.rst_stats()
