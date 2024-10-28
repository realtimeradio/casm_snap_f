import socket
import time
import datetime

from .block import Block
from ..error_levels import *
from .. import __version__
from .. import __fwversion__

import casperfpga.sysmon

VCCBRAM_MIN_WARN = 0.97
VCCBRAM_MAX_WARN = 1.03
VCCBRAM_MIN_ERR = -0.5
VCCBRAM_MAX_ERR = 1.1
VCCAUX_MIN_WARN = 1.71
VCCAUX_MAX_WARN = 1.89
VCCAUX_MIN_ERR = -0.5
VCCAUX_MAX_ERR = 2.
VCCINT_MIN_WARN = 0.97
VCCINT_MAX_WARN = 1.03
VCCINT_MIN_ERR = -0.5
VCCINT_MAX_ERR = 1.1
TEMP_MIN_WARN = 20.
TEMP_MAX_WARN = 65.
TEMP_MIN_ERR = 0. 
TEMP_MAX_ERR = 85.

FPGA_CLK_MAX_WARN = 255.
FPGA_CLK_MIN_WARN = 245.

class Xadc(casperfpga.sysmon.Sysmon):
    reg = 'xadc'

class Fpga(Block):
    """
    Instantiate a control interface for top-level FPGA control.

    :param host: CasperFpga interface for host.
    :type host: casperfpga.CasperFpga

    :param name: Name of block in Simulink hierarchy.
    :type name: str

    :param logger: Logger instance to which log messages should be emitted.
    :type logger: logging.Logger

    """
    def __init__(self, host, name, logger=None):
        # Top-level F-engine sees all registers
        super(Fpga, self).__init__(host, name, logger)
        self.sysmon = Xadc(self.host)

    def get_fpga_clock(self):
        """
        Estimate the FPGA clock, by polling the ``sys_clkcounter`` register.
        
        :return: Estimated FPGA clock in MHz
        :rtype: float

        """
        c0 = self.read_uint('sys_clkcounter')
        t0 = time.time()
        time.sleep(0.1)
        c1 = self.read_uint('sys_clkcounter')
        t1 = time.time()
        # Catch counter wrap
        if c1 < c0:
            c1 += 2**32
        clk_mhz = (c1 - c0) / 1e6 / (t1 - t0)
        return clk_mhz

    def get_firmware_version(self):
        """
        Read the firmware version register and return the contents as a string.

        :return version: major_version.minor_version.revision.bugfix
        :rtype str:
        """
        v = self.read_uint('version_version')
        major  = (v >> 24) & 0xff
        minor  = (v >> 16) & 0xff
        rev    = (v >>  8) & 0xff
        bugfix = (v >>  0) & 0xff
        return "%d.%d.%d.%d" % (major, minor, rev, bugfix)

    def check_firmware_support(self):
        """
        Check the software packages firmware support version against
        the running firmware version.

        :return: True if firmware is supported, False otherwise.
        :rtype bool:
        """
        vfw_str = self.get_firmware_version()
        vsw_str = __fwversion__
        vfw = vfw_str.split('.')
        vsw = vsw_str.split('.')
        # Check from major version down. If __fwversion__ says "A.B"
        # then any A.B.x.y is deemed supported.
        for vn, ver in enumerate(vsw):
            if len(ver) > 0 and ver != vfw[vn]:
                self._warning("Software supports FW rev %s, but not %s" % (vsw_str, vfw_str))
                return False
        return True

    def get_build_time(self):
        """
        Read the UNIX time at which the current firmware was built.

        :return build_time: Seconds since the UNIX epoch at which the running
            firmware was built.

        :rtype int:
        """
        t = self.read_uint('version_timestamp')
        return t

    def is_programmed(self):
        """
        Lazy check to see if a board is programmed.
        Check for the "version_version" register. If it exists, the board is deemed programmed.
        
        :return: True if programmed, False otherwise.
        :rtype: bool

        """
        return 'version_version' in self.listdev()

    def get_status(self):
        """
        Get status and error flag dictionaries.

        Status keys:

            - programmed (bool) : ``True`` if FPGA appears to be running DSP
              firmware. ``False`` otherwise, and flagged as a warning.

            - timestamp (str) : The current time, as an ISO format string.

            - fpga_clk_mhz (float) : The estimated FPGA clock rate in MHz. This
                is the same as the estimated ADC sampling rate.
              Flagged with an error if not between 190 and 200 MHz

            - host (str) : The host name of this board.

            - sw_version (str) : The version string of the control software
              package. Flagged as warning if the version indicates a build
              against a dirty git repository.

            - fw_supported (bool) : True if the running firmware is supported
              by this software. False (and flagged as an error) otherwise.

            - fw_version (str): The version string of the currently running
              firmware. Available only if the board is programmed.

            - fw_build_time (int): The build time of the firmware,
              as an ISO format string. Available only if the board 
              is programmed.

            - sys_mon (str) : ``'reporting'`` if the current firmware has a
              functioning system monitor module. Otherwise ``'not reporting'``,
              flagged as an error.

            - temp (float) : FPGA junction temperature, in degrees C. (Only
              reported is system monitor is available). Flagged as a warning
              if outside the recommended operating conditions. Flagged as an
              error if outside the absolute maximum ratings. See DS892.

            - vccaux (float) : Voltage of the VCCAUX FPGA power rail. (Only
              reported is system monitor is available). Flagged as a warning
              if outside the recommended operating conditions. Flagged as an
              error if outside the absolute maximum ratings. See DS892.

            - vccbram (float) : Voltage of the VCCBRAM FPGA power rail. (Only
              reported is system monitor is available). Flagged as a warning
              if outside the recommended operating conditions. Flagged as an
              error if outside the absolute maximum ratings. See DS892.

            - vccint (float) : Voltage of the VCCINT FPGA power rail. (Only
              reported is system monitor is available). Flagged as a warning
              if outside the recommended operating conditions. Flagged as an
              error if outside the absolute maximum ratings. See DS892.


        :return: (status_dict, flags_dict) tuple. `status_dict` is a dictionary of
            status key-value pairs. flags_dict is
            a dictionary with all, or a sub-set, of the keys in `status_dict`. The values
            held in this dictionary are as defined in `error_levels.py` and indicate
            that values in the status dictionary are outside normal ranges.
        """
        stats = {}
        flags = {}
        stats['programmed'] = self.is_programmed()
        stats['timestamp'] = datetime.datetime.now().isoformat()
        stats['host'] = self.host.host
        stats['sw_version'] = __version__
        fpga_clk_mhz = self.get_fpga_clock()
        stats['fpga_clk_mhz'] = fpga_clk_mhz
        if fpga_clk_mhz > FPGA_CLK_MAX_WARN or fpga_clk_mhz < FPGA_CLK_MIN_WARN:
            flags['fpga_clk_mhz'] = FENG_ERROR
        if stats['programmed']:
            stats['fw_version'] = self.get_firmware_version()
            stats['fw_build_time'] = datetime.datetime.fromtimestamp(self.get_build_time()).isoformat()
            stats['fw_supported'] = self.check_firmware_support()
            if not stats['fw_supported']:
                flags['fw_supported'] = FENG_ERROR
        try:
            stats.update(self.sysmon.get_all_sensors())
            stats['sys_mon'] = 'reporting'
            flags['sys_mon'] = FENG_OK
        except:
            stats['sys_mon'] = 'not reporting'
            flags['sys_mon'] = FENG_WARNING
        if not stats['programmed']:
            flags['programmed'] = FENG_ERROR
        if stats['sw_version'].endswith('dirty'):
            flags['sw_version'] = FENG_WARNING
        if 'vccaux' in stats:
            if stats['vccaux'] < VCCAUX_MIN_WARN or stats['vccaux'] > VCCAUX_MAX_WARN:
                flags['vccaux'] = FENG_WARNING
            if stats['vccaux'] < VCCAUX_MIN_ERR or stats['vccaux'] > VCCAUX_MAX_ERR:
                flags['vccaux'] = FENG_ERROR
        if 'vccbram' in stats:
            if stats['vccbram'] < VCCBRAM_MIN_WARN or stats['vccbram'] > VCCBRAM_MAX_WARN:
                flags['vccbram'] = FENG_WARNING
            if stats['vccbram'] < VCCBRAM_MIN_ERR or stats['vccbram'] > VCCBRAM_MAX_ERR:
                flags['vccbram'] = FENG_ERROR
        if 'vccint' in stats:
            if stats['vccint'] < VCCINT_MIN_WARN or stats['vccint'] > VCCINT_MAX_WARN:
                flags['vccint'] = FENG_WARNING
            if stats['vccint'] < VCCINT_MIN_ERR or stats['vccint'] > VCCINT_MAX_ERR:
                flags['vccint'] = FENG_ERROR
        if 'temp' in stats:
            if stats['temp'] < TEMP_MIN_WARN or stats['temp'] > TEMP_MAX_WARN:
                flags['temp'] = FENG_WARNING
            if stats['temp'] < TEMP_MIN_ERR or stats['temp'] > TEMP_MAX_ERR:
                flags['temp'] = FENG_ERROR
        return stats, flags
