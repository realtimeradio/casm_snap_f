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


DEFAULT_N_INPUTS = 12  # ADC inputs per SNAP
DEFAULT_N_CHANS = 2**12 # Frequency channels per input
DEFAULT_SAMPLE_RATE_HZ = 250000000
MAX_OUTPUT_OCCUPANCY = 0.9 # Only allow 3072 channels to be sent at 250 MHz sampling

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
    def __init__(self,
            host,
            logger=None,
            fpgfile=None,
            n_inputs=DEFAULT_N_INPUTS,
            n_chans=DEFAULT_N_CHANS,
            fs_hz=DEFAULT_SAMPLE_RATE_HZ
        ):
        self.hostname = host #: hostname of the F-Engine's host board
        #: Python Logger instance
        self.logger = logger or helpers.add_default_log_handlers(logging.getLogger(__name__ + ":%s" % (host)))
        #: F-engine sample rate, in Hz
        self.fs_hz = fs_hz
        #: Number of frequency channels per input signal
        self.n_chans = n_chans
        #: Number of ADC channels
        self.n_inputs = n_inputs
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
        self.noise       = noisegen.NoiseGen(self._cfpga, 'noise', n_noise=2, n_outputs=self.n_inputs)
        #: Control interface to Input Multiplex block
        self.input       = input.Input(self._cfpga, 'input', n_streams=16, n_real_streams=self.n_inputs, n_bits=8)
        #: Control interface to Coarse Delay block
        self.delay       = delay.Delay(self._cfpga, 'delay', n_streams=self.n_inputs)
        #: Control interface to PFB block
        self.pfb         = pfb.Pfb(self._cfpga, 'pfb')
        #: Control interface to Autocorrelation block
        self.autocorr    = autocorr.AutoCorr(self._cfpga, 'autocorr',
                                             acc_len=1024,
                                             n_signals=self.n_inputs,
                                             n_parallel_streams=1,
                                             n_cores=self.n_inputs//2,
                                             use_mux=True,
                                             )
        #: Control interface to Equalization block
        self.eq          = eq.Eq(self._cfpga, 'eq', n_inputs=self.n_inputs, n_parallel_inputs=self.n_inputs//2, n_coeffs=self.n_chans//8)
        #: Control interface to post-equalization Test Vector Generator block
        self.eqtvg       = eqtvg.EqTvg(self._cfpga, 'eqtvg', n_streams=self.n_inputs, n_parallel_streams=self.n_inputs//2, n_chans=self.n_chans)
        #: Control interface to Channel Reorder block
        self.reorder     = chanreorder.ChanReorder(self._cfpga, 'chan_reorder', n_chans=self.n_chans)
        #: Control interface to Packetizer block
        self.packetizer  = packetizer.Packetizer(self._cfpga, 'packetizer', sample_rate_mhz=self.fs_hz / 1.e6,
                n_signals=16, n_signals_real=self.n_inputs, n_chans=self.n_chans, n_words_per_block=4)
        #: Control interface to 10GbE interface block
        self.eth         = eth.Eth(self._cfpga, 'eth')
        #: Control interface to Correlation block
        self.corr        = corr.Corr(self._cfpga,'corr_0', n_chans=self.n_chans, n_signals=self.n_inputs)

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

    def _configure_output(self, dests, nchan_packet=512, feng_id=0):
        """
        Configure the channel reordering and packetizer configuration
        for chosen output parameters.

        :param dests: List of dictionaries describing where packets should be sent. Each
            list entry should have the following keys:

              - 'ip' : The destination IP (as a dotted-quad string) to which packets
                should be sent.
              - 'port' : The destination UDP port to which packets should be sent.
              - 'start_chan' : The first frequency channel number which should be sent
                to this IP / port.
              - 'nchan' : The number of channels which should be sent to this IP / port.
                ``nchan`` should be a multiple of ``nchan_packet``.
        :type dests: List of dict

        :param nchan_packet: Number of frequency channels in each output F-engine
            packet
        :type nchan_packet: int

        :param feng_id: Fengine ID to write to output UDP packet headers.
        :type feng_id: int

        :return: Raise ``RuntimeError`` if configuration is invalid.
        """

        # First check that each IP has an allowed number of output channels
        for dest in dests:
            assert "ip" in dest, "Each destination should have an 'ip' key"
            assert "port" in dest, "Each destination should have a 'port' key"
            assert "start_chan" in dest, "Each destination should have a 'start_chan' key"
            assert "nchan" in dest, "Each destination should have an 'nchan' key"
            ip = dest["ip"]
            nchan = dest["nchan"]
            if not dest["nchan"] % nchan_packet == 0:
                self.logger.error(f"Number of channels destined for {ip} ({nchan}) is not a multiple of packet size ({nchan_packet})")
                raise RuntimeError

        # Get packet parameters
        try:
            starts, payloads, chans = self.packetizer.get_packet_info(nchan_packet, MAX_OUTPUT_OCCUPANCY)
        except:
            self.logger.error("Failed to get packet boundary information. See eth.get_packet_info()")
            raise RuntimeError

        max_packets = len(starts)

        # Iterate though each packet and place channels appropriately
        pn = 0 # packet number
        pkt_dest_port = []
        pkt_dest_ip = []
        pkt_chan = []
        pkt_feng_id = []
        chan_map = np.zeros(self.n_chans, dtype=int)
        for dest in dests:
            npkt = dest["nchan"] // nchan_packet # packets to this address
            for p in range(npkt):
                if pn >= max_packets:
                    self.logger.error("Tried to fill more packets than are available!")
                    raise RuntimeError
                first_chan = dest["start_chan"] + p * nchan_packet # first chan in this packet
                chan_map[chans[pn]] = np.arange(first_chan, first_chan + nchan_packet)
                pkt_dest_ip += [dest["ip"]]
                pkt_dest_port += [dest["port"]]
                pkt_chan += [first_chan]
                pkt_feng_id += [feng_id]
                pn += 1

        # If we've made it to here, we have everything we need to configure the packetizer
        self.packetizer.write_config(
                starts[0:pn],
                payloads[0:pn],
                pkt_chan,
                pkt_feng_id,
                pkt_dest_ip,
                pkt_dest_port,
                self.n_inputs,
                nchan_packet,
                print_config=False,
        )

        self.reorder.set_channel_order(chan_map)


    def configure(self,
            source_ip = "100.100.100.100",
            source_port = 10000,
            program = True,
            fpgfile = None,
            dests = [{
                "ip" : "100.100.100.101",
                "port" : 10000,
                "start_chan" : 0,
                "nchan" : 3072,
                }],
            macs = {
                "100.100.100.100": 0x0202020a0a64,
                "100.100.100.101": 0x506b4bd3c660,
                },
            nchan_packet = 512,
            fft_shift = None,
            eq = None,
            sw_sync = False,
            enable_tx = True,
            feng_id = 0,
        ):
        """
        Completely configure a SNAP F-engine.

        :param source_ip: The IP address from which this board should send packets.
        :type source_ip: str

        :param source_port: The source UDP port from which F-engine packets should be sent.
        :type source_port: int

        :param program: If True, program the FPGA (either with the provided
            fpgfile or the currently loaded firmware).
            Also train the ADC-> FPGA links.
        :type program: bool

        :param fpgfile: Path to .fpg firmware file to load. If None, ask the SNAP board
            what it is currently running.
        :type fpgfile: str

        :param dests: List of dictionaries describing where packets should be sent. Each
            list entry should have the following keys:

              - 'ip' : The destination IP (as a dotted-quad string) to which packets
                should be sent.
              - 'port' : The destination UDP port to which packets should be sent.
              - 'start_chan' : The first frequency channel number which should be sent
                to this IP / port.
              - 'nchan' : The number of channels which should be sent to this IP / port.
                ``nchan`` should be a multiple of ``nchan_packet``.
        :type dests: List of dict

        :param macs: Dictionary, keyed by dotted-quad string IP addresses, containing
            MAC addresses for F-engine packet destinations. I.e., IP/MAC pairs for
            packet destinations, and for the source board.
        :type macs: dict

        :param nchan_packet: Number of frequency channels in each output F-engine
            packet
        :type nchan_packet: int

        :param fft_shift: If provided, set the F-engine FFT shift to the provided value.
        :type fft_shift: int

        :param eq: If provided, the list of pre-quantization equalization
            coefficients to be loaded to F-engines. This should be multidimensional with
            dimensions [n_inputs, eq.n_coeffs]
        :type eq: list

        :param sw_sync: If True, issue a software reset trigger, rather than waiting
            for an external reset pulse to be received over SMA.
        :type sw_sync: bool

        :param enable_tx: If True, enable 10 GbE F-Engine Ethernet output.
        :type enable_tx: bool

        :param feng_id: Fengine ID to write to output UDP packet headers.
        :type feng_id: int
        """

        if program:
            self.program(fpgfile)

        self.initialize()
        self.eth.reset() # Includes disable

        if fft_shift is not None:
            self.pfb.set_fftshift(fft_shift)

        if eq is not None:
            for eqi in eq:
                self.eq.set_coeffs(eqi)

        for ip, mac in macs.items():
            self.eth.add_arp_entry(ip, mac)

        for dest in dests:
            if dest["ip"] not in macs:
                self.logger.critical(f"IP {dest} has no MAC address specified. Your network might get flooded")

        if source_ip not in macs:
            self.logger.warning(f"Source IP {source_ip} has no MAC address")
            raise ValueError

        self.eth.configure_source(macs[source_ip], source_ip, source_port)
        self._configure_output(dests, nchan_packet, feng_id)

        self.update_timekeeping()

        self.sync.arm_sync(wait_for_sync=True)
        if sw_sync:
            self.sync.sw_sync()
        else:
            self.sync.wait_for_sync()

        # Only enable TX when the pipeline has been
        # Synchronized and is up and running
        self.eth.status_reset()
        if enable_tx:
            self.eth.enable_tx()
