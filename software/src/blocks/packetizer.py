import numpy as np
import struct

from .block import Block

PROTOCOL_OVERHEAD_BYTES = 16 + 18 + 20 + 8 # app + Eth + IP + UDP

class Packetizer(Block):
    """
    The packetizer block allows dynamic definition of
    packet sizes and contents.
    In firmware, it is a simple block which allows
    insertion of header entries  and EOFs at any point in the
    incoming data stream.
    It is up to the user to configure this block such that it
    behaves in a reasonable manner -- i.e.

       - Output data rate does not overflow the downstream Ethernet core
       - Packets have a reasonable size
       - EOFs and headers are correctly placed.

    :param host: CasperFpga interface for host.
    :type host: casperfpga.CasperFpga

    :param name: Name of block in Simulink hierarchy.
    :type name: str

    :param logger: Logger instance to which log messages should be emitted.
    :type logger: logging.Logger

    :param n_chans: Number of frequency channels in the correlation output.
    :type n_chans: int

    :param n_signals: Number of independent analog streams in the system including
        any dummy inputs.
    :type n_signals: int

    :param n_signals: Number of independent analog streams in the system excluding
        any dummy inputs.
    :type n_signals: int

    :param n_words_per_block: Granularity of packetizer words blocking. Blocks of channels
        may be sent or not sent only in chunks of ``words_per_block``.
    :type n_words_per_block: int

    :param sample_rate_mhz: ADC sample rate in MHz. Used for data rate checks.
    :type sample_rate_mhz: float
    """
    sample_width = 1 # Sample width in bytes: 4+4bit complex = 1 Byte
    word_width = 8 # Granularity of packet size in Bytes
    line_rate_gbps = 10 # Link speed in Gbits/s
    def __init__(self, host, name, n_chans=4096, n_signals=16, n_signals_real=12,
            n_words_per_block=8, sample_rate_mhz=200.0, logger=None):
        super(Packetizer, self).__init__(host, name, logger)
        self.n_chans = n_chans
        self.n_signals = n_signals
        self.n_signals_real = n_signals_real
        self.n_words_per_block = n_words_per_block
        self.sample_rate_mhz = sample_rate_mhz
        self.n_total_words = self.sample_width * self.n_chans * self.n_signals // self.word_width
        self.n_total_blocks = self.n_total_words // self.n_words_per_block
        self.n_words_per_chan = self.sample_width * self.n_signals // self.word_width
        self.full_data_rate_gbps = 8 * self.sample_width * self.n_signals_real * self.sample_rate_mhz * 1e6/2. / 1.0e9
        assert self.n_words_per_block % self.n_words_per_chan == 0, "Unsupported configuration!"
        self.n_chans_per_block = self.n_words_per_block // self.n_words_per_chan

    def get_packet_info(self, n_pkt_chans, occupation=0.95):
        """
        Get the packet boundaries for packets containing a given number of
        frequency channels.
        

        :param n_pkt_chans: The number of channels per packet.
        :type n_pkt_chans: int

        :param occupation: The maximum allowed throughput capacity of the underlying link.
            The calculation does not include application or protocol overhead,
            so must necessarily be < 1.
        :type occupation: float

        :return: packet_starts, packet_payloads, channel_indices

            ``packet_starts`` : list of ints
                The word indexes where packets start -- i.e., where headers should be
                written.
                For example, a value [0, 1024, 2048, ...] indicates that headers
                should be written into underlying brams at addresses 0, 1024, etc.
            ``packet_payloads`` : list of range()
                The range of indices where this packet's payload falls. Eg:
                [range(1,257), range(1025,1281), range(2049,2305), ... etc]
                These indices should be marked valid, and the last given an EOF.
            ``channel_indices`` : list of range()
                The range of channel indices this packet will send. Eg:
                [range(1,129), range(1025,1153), range(2049,2177), ... etc]
                Channels to be sent should be re-indexed so that they fall into
                these ranges.
        """
        assert n_pkt_chans % self.n_chans_per_block == 0, \
            "channels per packet must be a mulitple of channels per block"
        assert occupation < 1, "Link occupation must be < 1"
        pkt_size = n_pkt_chans * self.n_words_per_chan * self.word_width
        assert pkt_size <= 8192, "Can't send packets > 8192 bytes!"

        # Figure out what fraction of channels we can fit on the link
        self._info("Full data rate is %.2f Gbps" % self.full_data_rate_gbps)
        chan_frac = occupation * self.line_rate_gbps / self.full_data_rate_gbps
        target_throughput = occupation * self.line_rate_gbps
        self._info("Target maximum throughput is %.2f Gbps" % target_throughput)
        self._info("%.2f link occupation => Max %.2f bandwidth sent" % (occupation, chan_frac))
        # Round down to an integer number of channels
        n_sent_chans = int(np.floor(chan_frac * self.n_chans))
        self._info("%.2f link occupation => Max %.d channels sent" % (occupation, n_sent_chans))
        # Round down to a whole number of packets
        n_pkts = (n_sent_chans // n_pkt_chans)
        n_sent_chans = n_pkt_chans * n_pkts
        self._info("Will allocate %d channels in %d packets (%d channels each)" % (n_sent_chans, n_pkts, n_pkt_chans))
        n_sent_blocks = n_sent_chans // self.n_chans_per_block
        self._info("Will allocate %d blocks in %d packets" % (n_sent_blocks, n_pkts))

        overhead = (pkt_size + PROTOCOL_OVERHEAD_BYTES) / pkt_size
        actual_throughput = n_sent_chans / self.n_chans * self.full_data_rate_gbps
        actual_datarate = actual_throughput * overhead
        self._info("Actual throughput is %.2f Gbps" % actual_throughput)
        self._info("Packet size (payload only) is %d Bytes" % pkt_size)
        self._info("Actual data rate with overhead is %.2f Gbps" % actual_datarate)
        actual_occupancy = actual_datarate / self.line_rate_gbps
        self._info("Link occupancy is %.2f%%" % actual_occupancy)
        if actual_occupancy > 0.95:
            self._critical("Required data rate is %.2f%% of line rate. This is unlikely to work" % actual_occupancy)
        if actual_occupancy >= 1:
            self._error("Required data rate is >line rate. This will not work.")
            raise RuntimeError

        # Channels can only be sent in positions which are a multiple of n_chans_per_block 
        possible_chan_starts = range(0, self.n_chans, self.n_chans_per_block)
        # The first words of each packet
        possible_start_words = [c*self.n_words_per_chan for c in possible_chan_starts]
        #possible_start_words = [(c*self.n_words_per_chan + 1) for c in possible_chan_starts]

        # Now figure out how many of the total blocks we're going to use and divide up the deadtime
        n_blocks_used = n_sent_chans // self.n_chans_per_block
        spare_blocks = self.n_total_blocks - n_blocks_used
        spare_words = spare_blocks * self.n_words_per_block
        self._info("Number of blocks used: %d" % n_blocks_used)
        self._info("Number of blocks spare: %d" % spare_blocks)

        assert spare_words % self.n_words_per_chan == 0, "This shouldn't be possible!"
        assert spare_words >= 0, "Configuration doesn't have space for header words"
        # Allocate enough words per packet for the data and header
        spare_chans_per_packet = ((self.n_chans - n_sent_chans) // n_pkts)
        self._info("Number of spare chans per packet: %d" % spare_chans_per_packet)
        # Round down to whole number of blocks
        spare_chans_per_packet = self.n_chans_per_block * (spare_chans_per_packet // self.n_chans_per_block)
        self._info("Using %d spare chans per packet" % spare_chans_per_packet)
        packet_starts = []
        packet_payloads = []
        channel_indices = []
        w_cnt = 0
        for pkt in range(n_pkts):
            assert w_cnt % self.n_words_per_block == 0
            packet_starts += [w_cnt // self.n_words_per_block]
            #w_cnt += 1
            # Find place we can start a payload
            for i in possible_start_words:
                if i >= w_cnt:
                    w_cnt = i
                    break
            assert w_cnt % self.n_words_per_block == 0
            assert (w_cnt + n_pkt_chans * self.n_words_per_chan) % self.n_words_per_block == 0
            packet_payloads += [
                    range(w_cnt // self.n_words_per_block,
                    (w_cnt + n_pkt_chans * self.n_words_per_chan) // self.n_words_per_block)
                    ]
            # And which channels would these be?
            channel_indices += [range(w_cnt // self.n_words_per_chan,
                                      w_cnt // self.n_words_per_chan + n_pkt_chans)]
            w_cnt += n_pkt_chans * self.n_words_per_chan
            assert (w_cnt < self.n_total_words), \
                "Packet %d: Tried to allocate word %d > %d" % (pkt, w_cnt, self.n_total_words)
            # Add in padding space
            w_cnt += spare_chans_per_packet * self.n_words_per_chan
        return packet_starts, packet_payloads, channel_indices

    def _format_flags(self, is_header=False, is_valid=False, is_eof=False):
        flags = (int(is_eof) << 2) + (int(is_valid) << 1) + (int(is_header) << 0)
        return flags

    def _format_ant_chan(self, ant, chan):
        return (ant << 16) + (chan << 0)

    def _deformat_ant_chan(self, ant_chan):
        chan = ant_chan & 0xffff
        ant = (ant_chan >> 16) & 0xffff
        return ant, chan

    def _deformat_flags(self, f):
        is_eof = bool((f >> 2) & 1)
        is_vld = bool((f >> 1) & 1)
        is_hdr = bool((f >> 0) & 1)
        return is_hdr, is_vld, is_eof

    def print_config(self, n=None):
        """
        Print the contents of the packetizer configuration registers.
        Good for debugging.

        :param n: Number of block entries to print. If None, print everything
        :type n: int
        """

        if n is None:
            n = self.n_total_blocks

        ant_chans = np.frombuffer(self.read('ant_chan', self.n_total_blocks * 4), dtype='>u4')
        ips   = np.frombuffer(self.read('ips', self.n_total_blocks * 4), dtype='>u4')
        ports = np.frombuffer(self.read('ports', self.n_total_blocks * 2), dtype='>u2')
        flags = np.frombuffer(self.read('flags', self.n_total_blocks * 1), dtype='>u1')

        print('pkt : chan  ant  port  ip')
        for i in range(n):
            is_hdr, is_vld, is_eof = self._deformat_flags(flags[i])
            ant, chan = self._deformat_ant_chan(ant_chans[i])
            print('%4d: %4d %3d %.5d 0x%.8x' % (i, chan, ant, ports[i], ips[i]), end=' ')
            if is_vld:
                print('valid', end=' ')
            if is_hdr:
                print('header', end=' ')
            if is_eof:
                print('EOF', end=' ')
            print()
        
    def write_config(self, packet_starts, packet_payloads, channel_indices,
            ant_indices, dest_ips, dest_ports, n_pkt_antpols, n_pkt_chans, print_config=False):
        """
        Write the packetizer configuration BRAMs with appropriate entries.

        :param packet_starts:
            Word-indices which are the first entry of a packet and should
            be populated with headers (see `get_packet_info()`)
        :type packet_starts: list of int

        :param packet_payloads:
            Word-indices which are data payloads, and should be mared as
            valid (see `get_packet_info()`)
        :type packet_payloads: list of range()s

        :param channel_indices:
            Header entries for the channel field of each packet to be sent
        :type channel_indices: list of ints

        :param ant_indices:
            Header entries for the antenna field of each packet to be sent
        :type ant_indices: list of ints

        :param dest_ips: list of str
            IP addresses for each packet to be sent.
        :type dest_ips:

        :param dest_ports:
            UDP destination ports for each packet to be sent.
        :type dest_ports: list of int

        :param n_pkt_chans: Number of channels per packet.
        :type n_pkt_chans: int

        :param n_pkt_antpols: Numper of antpols per packet.
        :type n_pkt_antpols: int

        :param print:
            If True, print config for debugging
        :type print: bool

        All parameters should have identical lengths.
        """


        def ip2int(x):
            octets = list(map(int, x.split('.')))
            ip = 0
            ip += (octets[0] << 24)
            ip += (octets[1] << 16)
            ip += (octets[2] << 8)
            ip += (octets[3] << 0)
            return ip

        n_packets = len(packet_starts)
        assert len(packet_payloads) == n_packets
        assert len(channel_indices) == n_packets
        assert len(ant_indices) == n_packets
        assert len(dest_ips) == n_packets
        assert len(dest_ports) == n_packets

        ant_chans = [0] * self.n_total_blocks
        ips       = [0] * self.n_total_blocks
        ports     = [0] * self.n_total_blocks
        flags     = [0] * self.n_total_blocks

        for i in range(n_packets):
            ant_chans[packet_starts[i]] = self._format_ant_chan(ant_indices[i], channel_indices[i])
            flags[packet_starts[i]] = self._format_flags(is_header=True, is_valid=True)
            for w in packet_payloads[i]:
                flags[w] = self._format_flags(is_header= w==packet_starts[i], is_valid=True)
            # Insert the Destination IP synchronous with the EOF
            ips[w]   = ip2int(dest_ips[i])
            ports[w] = dest_ports[i]
            # Overwrite the last entry with the EOF
            flags[w] = self._format_flags(is_header=False, is_valid=True, is_eof=True)

        self.write('ant_chan', struct.pack('>%dI' % self.n_total_blocks, *ant_chans))
        self.write('ips',   struct.pack('>%dI' % self.n_total_blocks, *ips))
        self.write('ports', struct.pack('>%dH' % self.n_total_blocks, *ports))
        self.write('flags', struct.pack('>%dB' % self.n_total_blocks, *flags))
        self.write_int('n_chans', n_pkt_chans)
        self.write_int('n_pols', n_pkt_antpols)

        if print_config:
            self.print_config(self.n_total_blocks)
