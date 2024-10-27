F-Engine System Overview
========================

Overview
--------

The CASM F-Engine firmware is designed to run on a SNAP [1]_ FPGA board, and provides channelization of 12 analog data streams, sampled at up to 250 Msps, into 4096 sub-bands.

After channelization, data words are requantized to 4-bit resolution (4-bit real + 4-bit imaginary) and a subset of the 4096 generated frequency channels are output as a UDP/IP stream over a single 40 Gb/s Ethernet interface.

The top-level specs of the F-Engine are:

+-------------------------+----------+----------------------+
| Parameter               | Value    | Notes                |
+=========================+==========+======================+
| Number of analog inputs | 12       |                      |
|                         |          |                      |
+-------------------------+----------+----------------------+
| Maximum sampling rate   | 250 Msps | Limited by ADC speed |
|                         |          | & timing constraint  |
|                         |          | target               |
+-------------------------+----------+----------------------+
| Test inputs             | Noise;   | Firmware contains 2  |
|                         | zeros    | independent gaussian |
|                         |          | noise generators.    |
|                         |          | Any of the 12 data   |
|                         |          | streams may be       |
|                         |          | replaced with any of |
|                         |          | these digital noise  |
|                         |          | sources, or zeros.   |
+-------------------------+----------+----------------------+
| Delay compensation      | <=7      | Programmable per-    |
|                         | samples  | input between 0 and  |
|                         |          | 7 samples. Mostly    |
|                         |          | useful for testing   |
+-------------------------+----------+----------------------+
| Polyphase Filter Bank   | 4096     |                      |
| Channels                |          |                      |
+-------------------------+----------+----------------------+
| Polyphase Filter Bank   | Hamming; |                      |
| Window                  | 4-tap    |                      |
+-------------------------+----------+----------------------+
| Polyphase Filter Bank   | 8 bits   |                      |
| Input Bitwidth          |          |                      |
+-------------------------+----------+----------------------+
| FFT Coefficient Width   | 18 bits  |                      |
+-------------------------+----------+----------------------+
| FFT Data Path Width     | 18 bits  |                      |
+-------------------------+----------+----------------------+
| Post-FFT Scaling        | 16       |                      |
| Coefficient Width       |          |                      |
+-------------------------+----------+----------------------+
| Post-FFT Scaling        | 4        |                      |
| Coefficient Binary      |          |                      |
| Point                   |          |                      |
+-------------------------+----------+----------------------+
| Number of Post-FFT      | 256      | One coefficient per  |
| Scaling Coefficients    |          | analog input. One    |
|                         |          | coefficient per 16   |
|                         |          | frequency channels   |
+-------------------------+----------+----------------------+
| Post-Quantization Data  | 4        | 4-bit real; 4-bit    |
| Bitwidth                |          | imaginary            |
+-------------------------+----------+----------------------+
| Frequency Channels      | <=3072   | Runtime              |
| Output                  |          | programmable.        |
|                         |          | Maximum is set by    |
|                         |          | total data rate      |
|                         |          | which is limited to  |
|                         |          | 10Gb/s (including    |
|                         |          | protocol overhead).  |
|                         |          | 3072 channels =      |
|                         |          | approx 9Gb/s         |
|                         |          | + overhead           |
+-------------------------+----------+----------------------+

A block diagram of the F-engine -- which is also the top-level of the Simulink source code for the firmware -- is shown in :numref:`feng_firmware_top`.

.. figure:: _static/figures/feng_firmware_annotated.pdf
    :align: center
    :name: feng_firmware_top

    F-Engine top-level Simulink diagram.

Initialization
++++++++++++++

The functionality of individual blocks is described below.
However, in order to simply get the firmware into a basic working state the following process should be followed:

  1. Program the FPGA
  2. Initialize all blocks in the system
  3. Trigger master reset and timing synchronization event.

In a multi-board system, the process of synchronizing a board can be relatively involved.
For testing purposes, using single board, a simple software reset can be used in place of a hardware timing signal to perform an artificial synchronization.
A software reset is automatically issued as part of system initialization.

The following commands bring the F-engine firmware into a functional state, suitable for testing.
See :numref:`control-interface` for a full software API description

.. code-block:: python

  # Import the SNAP F-Engine library
  from casm_f import snap_fengine

  # Instantiate a SnapFengine instance to a board with
  # hostname 'snap'
  f = snap_fengine.SnapFengine('snap')

  # Program a board
  f.program(path-to-fpg-file) # Load an fpg firmware binary

  # Initialize all the firmware blocks
  # and issue a global software reset
  f.initialize(read_only=False)


Block Descriptions
++++++++++++++++++

Each block in the firmware design can be controlled using an API described in :numref:`control-interface`. Here the basic functionality of each block is described.

.. [1]
    See `the CASPER SNAP wiki page <https://casper.berkeley.edu/wiki/SNAP>`__

