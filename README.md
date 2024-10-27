
## Building firmware

Dependencies:

- MATLAB / Simulink R2021a
- Xilinx Vivado / System Generator 2021.2


First, open Simulink:

```
cd firmware
./startsg
```

Then, in the MATLAB prompt, run the build script:

```
build_top
```

On the first run, this will build various DSP IP cores.
Subsequent runs may skip this step and should complete more quickly.

## Installing Raspberry Pi software

A raspberry pi OS image, which includes a CASPER `katcp` server is available at [TBC].

The version of the `tcpborphserver` installed in this image is available at `software/lib/katcp_devel`

## Installing control software

Dependencies:

- Python >=3.8

### Installing `casperfpga`

An appropriate version of casperfpga is available as a git submodule within this repository.
Install it as follows:

```
git submodule init software/lib/casperfpga
git submodule update software/lib/casperfpga
cd software/lib/casperfpga
pip install .
```
