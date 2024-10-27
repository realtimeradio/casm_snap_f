Output Data Formats
===================

This section defines the output packet formats for each of the pipeline
output data products. Unless otherwise specified, all data products are
transmitted in network- (i.e. big-) endian format.

Packet sizing is partially determined by the pipeline configuration.
Specifically:

-  ``NCHAN`` – The number of channels per packet.

-  ``NINPUTS`` – The number of input RF signals on an FPGA board.

In this design:

-  ``NCHAN`` = TBC

-  ``NINPUT`` = 12 

Voltage Packets
---------------

Data from the SNAP board(s) are transmitted as a series of UDP
packets, with each packet carrying data for multiple frequencies and multiple inputs.
Each packet has an 8 byte header followed by a payload of 4+4 bit complex signed integer data.

Packets are formatted as:

.. code:: C

      struct voltage_packet {
      };

Packet fields are as follows:

.. list-table::
  :widths: 30 30 10 100
  :header-rows: 1
  :align: left

  * - Field
    - Format
    - Units
    - Description

  * - ``sync_time``
    - ??
    - UNIX seconds
    - The timestamp of the spectra in the packet, referenced to ??

  * - ``chan0``
    - ??
    - channel number
    - The index of the first frequency channel in this packet's data payload

  * - ``input0``
    - ??
    - input number
    - The index of the first input in this packet’s data payload.
