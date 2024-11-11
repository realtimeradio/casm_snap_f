import logging
import socket
import inspect
import numpy as np
import struct
import time
import datetime
import os
import yaml
import casperfpga
from . import helpers
from . import __version__
from .error_levels import *
from .blocks import block
from .blocks import fpga
from .blocks import adc
from .blocks import sync
from .blocks import noisegen
from .blocks import input
from .blocks import delay
from .blocks import pfb
from .blocks import autocorr
from .blocks import eq
from .blocks import eqtvg
from .blocks import chanreorder
from .blocks import packetizer
from .blocks import eth
from .blocks import corr

PIPELINES_PER_XENG = 4

N_INPUTS = 12  # ADC inputs per SNAP
N_CHANS  = 2**12 # Frequency channels per input
FENG_SOURCE_PORT = 10000 # UDP source port for data transmission
MAC_BASE = 0x020203030400 # MAC base address for 10GbE interface
IP_BASE = (10 << 24) + (41 << 16) + (0 << 8) + 100 # IP base address for 10GbE interface
DEFAULT_SAMPLE_RATE_HZ = 250000000

class SnapFengine():
    """
    A control class for CASM's SNAP F-Engine firmware.

    :param host: Hostname of SNAP board
    :type host: str

    :param logger: Logger instance to which log messages should be emitted.
    :type logger: logging.Logger

    :param fpgfile: If provided, scrape information from the fpgfile. If not provided,
        attempt to ask the board for information about what firmware it is running.
    :type fpgfile: str

    :param fs_hz: ADC sample rate, in Hz.
    :typoe fs_hz: int

    """
    def __init__(self, host, logger=None, fpgfile=None, fs_hz=DEFAULT_SAMPLE_RATE_HZ):
        self.hostname = host #: hostname of the F-Engine's host board
        #: Python Logger instance
        self.logger = logger or helpers.add_default_log_handlers(logging.getLogger(__name__ + ":%s" % (host)))
        #: F-engine sample rate, in Hz
        self.fs_hz = fs_hz
        #: Underlying CasperFpga control instance
        self._cfpga = casperfpga.CasperFpga(
                        host=self.hostname,
                        transport=casperfpga.KatcpTransport,
                    )
        self.blocks = {}
        if fpgfile is not None or self._cfpga.is_running():
            try:
                self._cfpga.get_system_information(fpgfile)
            except:
                if fpgfile is not None:
                    self.logger.error(f"Failed to read and decode {fpgfile}")
                elif self._cfpga.is_running():
                    self.logger.error("Failed to get running firmware information from board even though it is programmed.")
        try:
            self._initialize_blocks()
        except:
            self.logger.exception("Failed to initialize firmware blocks. "
                                  "Maybe the board needs programming.")

    def is_connected(self):
        """
        :return: True if there is a working connection to a SNAP2. False otherwise.
        :rtype: bool
        """
        return self._cfpga.is_connected()

    def _initialize_blocks(self):
        """
        Initialize firmware blocks, populating the ``blocks`` attribute.
        """

        # blocks
        #: Control interface to high-level FPGA functionality
        self.fpga        = fpga.Fpga(self._cfpga, "")
        #: Control interface to ADC block
        self.adc         = adc.Adc(self._cfpga, 'adc', sample_rate_mhz=self.fs_hz / 1.e6)
        #: Control interface to Synchronization / Timing block
        self.sync        = sync.Sync(self._cfpga, 'sync', use_loopback=True, fs_hz=self.fs_hz)
        #: Control interface to Noise Generation block
        self.noise       = noisegen.NoiseGen(self._cfpga, 'noise', n_noise=2, n_outputs=N_INPUTS)
        #: Control interface to Input Multiplex block
        self.input       = input.Input(self._cfpga, 'input', n_streams=16, n_real_streams=N_INPUTS, n_bits=8)
        #: Control interface to Coarse Delay block
        self.delay       = delay.Delay(self._cfpga, 'delay', n_streams=N_INPUTS)
        #: Control interface to PFB block
        self.pfb         = pfb.Pfb(self._cfpga, 'pfb')
        #: Control interface to Autocorrelation block
        self.autocorr    = autocorr.AutoCorr(self._cfpga, 'autocorr',
                                             acc_len=1024,
                                             n_signals=N_INPUTS,
                                             n_parallel_streams=1,
                                             n_cores=N_INPUTS//2,
                                             use_mux=True,
                                             )
        #: Control interface to Equalization block
        self.eq          = eq.Eq(self._cfpga, 'eq', n_inputs=N_INPUTS, n_parallel_inputs=N_INPUTS//2, n_coeffs=N_CHANS//8)
        #: Control interface to post-equalization Test Vector Generator block
        self.eqtvg       = eqtvg.EqTvg(self._cfpga, 'eqtvg', n_streams=N_INPUTS, n_parallel_streams=N_INPUTS//2, n_chans=N_CHANS)
        #: Control interface to Channel Reorder block
        self.reorder     = chanreorder.ChanReorder(self._cfpga, 'chan_reorder', n_chans=N_CHANS)
        #: Control interface to Packetizer block
        self.packetizer  = packetizer.Packetizer(self._cfpga, 'packetizer', sample_rate_mhz=self.fs_hz / 1.e6,
                n_signals=16, n_signals_real=N_INPUTS, n_chans=N_CHANS, n_words_per_block=4)
        #: Control interface to 10GbE interface block
        self.eth         = eth.Eth(self._cfpga, 'eth')
        #: Control interface to Correlation block
        self.corr        = corr.Corr(self._cfpga,'corr_0', n_chans=N_CHANS, n_signals=N_INPUTS)

        # The order here can be important, blocks are initialized in the
        # order they appear here

        #: Dictionary of all control blocks in the firmware system.
        self.blocks = {
            'fpga'      : self.fpga,
            'adc'       : self.adc,
            'sync'      : self.sync,
            'noise'     : self.noise,
            'input'     : self.input,
            'delay'     : self.delay,
            'pfb'       : self.pfb,
            'eq'        : self.eq,
            'eqtvg'     : self.eqtvg,
            'reorder'   : self.reorder,
            'packetizer': self.packetizer,
            'eth'       : self.eth,
            'autocorr'  : self.autocorr,
            'corr'      : self.corr,
        }
        for blockname, block in self.blocks.items():
            block.initialize(read_only=True)


    def initialize(self):
        """
        Call the ```initialize`` methods of all underlying blocks (apart from
        the ADC block, which is initialized during programming), then
        issue a software global reset.

        """
        for blockname, block in self.blocks.items():
            if blockname == "adc":
                continue
            self.logger.info(f"Initializing block {blockname}")
            block.initialize()
        self.logger.info("Performing software global reset")
        self.sync.arm_sync()
        self.sync.sw_sync()

    def get_status_all(self):
        """
        Call the ``get_status`` methods of all blocks in ``self.blocks``.
        If the FPGA is not programmed with F-engine firmware, will only
        return basic FPGA status.

        :return: (status_dict, flags_dict) tuple.
            Each is a dictionary, keyed by the names of the blocks in
            ``self.blocks``. These dictionaries contain, respectively, the
            status and flags returned by the ``get_status`` calls of
            each of this F-Engine's blocks.
        """
        stats = {}
        flags = {}
        if not self.blocks['fpga'].is_programmed():
            stats['fpga'], flags['fpga'] = self.blocks['fpga'].get_status()
        else:
            for blockname, block in self.blocks.items():
                try:
                    stats[blockname], flags[blockname] = block.get_status()
                except:
                    self.logger.info("Failed to poll stats from block %s" % blockname)
        return stats, flags

    def print_status_all(self, use_color=True, ignore_ok=False):
        """
        Print the status returned by ``get_status`` for all blocks in the system.
        If the FPGA is not programmed with F-engine firmware, will only
        print basic FPGA status.

        :param use_color: If True, highlight values with colors based on
            error codes.
        :type use_color: bool

        :param ignore_ok: If True, only print status values which are outside the
           normal range.
        :type ignore_ok: bool

        """
        if not self.blocks['fpga'].is_programmed():
            print('FPGA stats (not programmed with F-engine image):')
            self.blocks['fpga'].print_status()
        else:
            for blockname, block in self.blocks.items():
                print('Block %s stats:' % blockname)
                block.print_status(use_color=use_color, ignore_ok=ignore_ok)

    def deprogram(self):
        """
        Reprogram the FPGA into its default boot image.
        """
        self._cfpga.transport.progdev(0)

    def set_equalization(self, eq_start_chan=1000, eq_stop_chan=3300, 
            start_chan=512, stop_chan=3584, filter_ksize=21, target_rms=0.125*3):
        """
        Set the equalization coefficients to realize a target RMS.

        :param eq_start_chan: Frequency channels below ``eq_start_chan`` will be given the same EQ coefficient
            as ``eq_start_chan``.
        :type eq_start_chan: int

        :param eq_stop_chan: Frequency channels above ``eq_stop_chan`` will be given the same EQ coefficient
            as ``eq_stop_chan``.
        :type eq_stop_chan: int

        :param start_chan: Frequency channels below ``start_chan`` will be given zero EQ coefficients.
        :type start_chan: int

        :param stop_chan: Frequency channels above ``stop_chan`` will be given zero EQ coefficients.
        :type stop_chan: int

        :param filter_ksize: Filter kernel size, for rudimentary RFI removal. This should be an odd value.
        :type filter_ksize: int

        :param target_rms: The target post-EQ RMS. This is normalized such that 0.875 is the saturation level.
            I.e., an RMS of 0.125 means that the RMS is one LSB of a 4-bit signed signal.
        :type target_rms: float

        """
        n_cores = self.autocorr.n_signals // self.autocorr.n_signals_per_block
        for i in range(n_cores):
            spectra = self.autocorr.get_new_spectra(i, filter_ksize=filter_ksize)
            n_signals, n_chans = spectra.shape
            coeff_repeat_factor = n_chans // self.eq.n_coeffs
            for j in range(n_signals):
                stream_id = i*n_signals + j
                self.logger.info("Trying to EQ input %d" % stream_id)
                pre_quant_rms = np.sqrt(spectra[j] / 2) # RMS of each real / imag component making up spectra
                eq_scale = self.eq.get_coeffs(stream_id)
                eq_scale = eq_scale.repeat(coeff_repeat_factor)
                curr_rms = pre_quant_rms * eq_scale
                diff = target_rms / curr_rms
                new_eq = eq_scale * diff
                # stretch the edge coefficients outside the pass band to avoid them heading to infinity
                new_eq[0:eq_start_chan] = new_eq[eq_start_chan]
                new_eq[eq_stop_chan:] = new_eq[eq_stop_chan]
                new_eq[0:start_chan] = 0
                new_eq[stop_chan:] = 0
                self.eq.set_coeffs(stream_id, new_eq[::coeff_repeat_factor])

    def program(self, fpgfile=None, initialize_adc=True):
        """
        Program an .fpg file to an FPGA. 

        :param fpgfile: The .fpg file to be loaded. Should be a path to a
            valid .fpg file. If None is given, the image currently loaded
            will be rebooted.
        :type fpgfile: str

        :param initialize_adc: If True, perform ADC link training. Otherwise skip.
            You _must_ perform link training before expecting ADC output to be meaningful.
        :type initialize_adc: bool

        """

        if not isinstance(fpgfile, str):
            raise TypeError("wrong type for fpgfile")

        # Resolve symlinks
        if fpgfile:
            fpgfile = os.path.realpath(fpgfile)

        if fpgfile and not os.path.exists(fpgfile):
            raise RuntimeError("Path %s doesn't exist" % fpgfile)

        self._cfpga.upload_to_ram_and_program(fpgfile)
        self._initialize_blocks()
        if initialize_adc:
            self.adc.initialize()

    def update_timekeeping(self):
        """
        Update internal timekeeping logic.
        """
        self.sync.update_telescope_time()
        # Wait for a couple of sync pulses to ensure period
        # is known to firmware
        self.sync.wait_for_sync()
        self.sync.wait_for_sync()
        self.sync.update_internal_time()

    def configure(self,
            source_ip = "100.100.100.100",
            source_port = 10000,
            program = True,
            fpgfile = None,
            dests = {
                "100.100.100.101": [0,128],
                },
            macs = {
                "100.100.100.100": 0x0202020a0a64,
                "100.100.100.101": 0x0202020a0a65,
                },
            nchan_packet = 16,
            fft_shift = None,
            eq = None,
            sw_sync = False,
            enable_tx = True,
            ):

        if program:
            self.program(fpgfile)

        self.initialize()
        self.eth.disable_tx() # Make explicit even though it is in initialize

        if fft_shift is not None:
            self.pfb.set_fftshift(fft_shift)

        if eq is not None:
            for eqi in eq:
                self.eq.set_coeffs(eqi)

        self.update_timekeeping()

        for ip, mac in macs.items():
            self.eth.add_arp_entry(ip, mac)

        for dest, dest_chans in dests.items():
            if dest not in macs:
                self.logger.warning(f"IP {dest} has not MAC address. Your network might get flooded")

        if source_ip not in macs:
            self.logger.error(f"Source IP {source_ip} has not MAC address")
            raise ValueError

        self.eth.configure_source(macs[source_ip], source_ip, source_port)

        self.sync.arm_sync()
        if sw_sync:
            self.sync.sw_sync()

        if enable_tx:
            self.eth.enable_tx()
