
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

A Raspberry Pi 4 OS image, which includes a CASPER `katcp` server is available at [TBC].

The version of the `tcpborphserver` installed in this image is available at `software/lib/katcp_devel`

### Recreating the Raspberry Pi image

1. Build a stock Raspbian image using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Be sure to enable the SSH client when creating the image.
2. Log into the Raspberry Pi with the username / password provided when creating the image, and enable SPI using the `raspi-config` utility (follow the `Interface Options` menu.
3. Disable WiFi and Bluetooth by adding the following to `/boot/firmware/config.txt` prior to the `[cm4]` entry:
  ```
  dtoverlay=disable-wifi
  dtoverlay=disable-bt
  ```
4. Install the tcpborphserver software
  1. Clone this repository
  2. Clone the latest `software/lib/katcp_devel` submodule with
  ```
  git submodule init software/lib/katcp_devel
  git submodule update
  ```
  3. Build `tcpborphserver3`
  ```
  cd software/lib/katcp_devel
  make
  ```
  4. Configure `tcpborphserver3` to start on boot:

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
