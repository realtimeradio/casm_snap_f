.. _control-interface:

Control Interface
=================

Overview
--------

A Python class ``SnapFengine`` is provided to encapsulate control
of individual blocks in the firmware DSP pipeline.
The structure of the software interface aims to mirror the hierarchy of
the firmware modules, through the use of multiple ``Block`` class instances,
each of which encapsulates control of a single module in the firmware pipeline.

In testing, and interactive debugging, the ``SnapFengine`` class provides
an easy way to probe board status for a SNAP board on the local network.

``SnapFengine`` Python Interface
---------------------------------

The ``SnapFengine`` class can be instantiated and used to control
a single SNAP board running CASM's F-Engine firmware. An example is below:


.. code-block:: python

  # Import the SNAP F-Engine library
  from casm_f import snap_fengine

  # Instantiate a SnapFengine instance to a board with
  # hostname 'snap'
  f = snap_fengine.SnapFengine('snap')

  # Program a board (if it is not already programmed)
  # and initialize all the firmware blocks
  if not f.fpga.is_programmed():
    f.program(path-to-fpg-file) # Load an fpg firmware binary
    # Initialize firmware blocks, including ADC link training
    f.initialize(read_only=False)

  # Blocks are available as items in the SnapFengine `blocks`
  # dictionary, or can be accessed directly as attributes
  # of the SnapFengine.

  # Print available block names
  print(sorted(f.blocks.keys()))
  # Returns:
  # ['adc', 'autocorr', 'corr', 'delay', 'eq', 'eq_tvg', 'eth',
  # 'fpga', 'input', 'noise', 'packetizer', 'pfb', 'reorder', 'sync']

  # Grab some ADC data from the first ADC input
  adc_data = f.adc.get_snapshot()
  print(adc_data.shape) # returns (12 [ADC inputs], 1024 [time samples])

Details of the methods provided by individual blocks are given in the next
section.


Top-Level Control
+++++++++++++++++

The Top-level ``SnapFengine`` instance can be used to perform high-level
control of the firmware, such as programming and de-programming FPGA boards.
It can also be used to apply configurations which affect multiple firmware
subsystems, such as configuring channel selection and packet destination.

Finally, a ``SnapFengine`` instance can be used to initialize, or get status
from, all underlying firmware modules.

.. autoclass:: casm_f.snap2_fengine.SnapFengine
  :no-show-inheritance:
  :members:

.. _control-fpga:

FPGA Control
++++++++++++

The ``FPGA`` control interface allows gathering of FPGA statistics such
as temperature and voltage levels. Its methods are functional regardless of
whether the FPGA is programmed with an CASM F-Engine firmware design.

.. autoclass:: casm_f.blocks.fpga.Fpga
  :no-show-inheritance:
  :members:

Timing Control
++++++++++++++

The ``Sync`` control interface provides an interface to configure and monitor the
multi-SNAP2 timing distribution system.

.. autoclass:: casm_f.blocks.sync.Sync
  :no-show-inheritance:
  :members:

.. _control-adc:

ADC Control
+++++++++++

The ``Adc`` control interface allows link training (aka "calibration") of
the ADC->FPGA data link.

.. autoclass:: casm_f.blocks.adc.Adc
  :no-show-inheritance:
  :members:

Input Control
+++++++++++++

.. autoclass:: casm_f.blocks.input.Input
  :no-show-inheritance:
  :members:

Noise Generator Control
+++++++++++++++++++++++

.. autoclass:: casm_f.blocks.noisegen.NoiseGen
  :no-show-inheritance:
  :members:


Delay Control
+++++++++++++

.. autoclass:: casm_f.blocks.delay.Delay
  :no-show-inheritance:
  :members:


PFB Control
+++++++++++

.. autoclass:: casm_f.blocks.pfb.Pfb
  :no-show-inheritance:
  :members:

Auto-correlation Control
++++++++++++++++++++++++

.. autoclass:: casm_f.blocks.autocorr.AutoCorr
  :no-show-inheritance:
  :members:


Correlation Control
+++++++++++++++++++

.. autoclass:: casm_f.blocks.corr.Corr
  :no-show-inheritance:
  :members:

Post-FFT Test Vector Control
++++++++++++++++++++++++++++

.. autoclass:: casm_f.blocks.eqtvg.EqTvg
  :no-show-inheritance:
  :members:

Equalization Control
++++++++++++++++++++

.. autoclass:: casm_f.blocks.eq.Eq
  :no-show-inheritance:
  :members:

Channel Selection Control
+++++++++++++++++++++++++

.. autoclass:: casm_f.blocks.chanreorder.ChanReorder
  :no-show-inheritance:
  :members:

Packetization Control
+++++++++++++++++++++

.. autoclass:: casm_f.blocks.packetizer.Packetizer
  :no-show-inheritance:
  :members:

Ethernet Output Control
+++++++++++++++++++++++

.. autoclass:: casm_f.blocks.eth.Eth
  :no-show-inheritance:
  :members:
