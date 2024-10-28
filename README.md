
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

A Raspberry Pi 4 OS image, which includes a CASPER `katcp` server is available [here](https://drive.google.com/file/d/1QGDiUgmDarjRJckHoHk1vYaPTGZHGnkt/view?usp=sharing)

The username / password (which can be used for SSH as well as local access) is `pi`/`CasperSnapPi`

The version of the `tcpborphserver` installed in this image is available in this repository at `software/lib/katcp_devel`

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
  sudo make install
  ```
  4. Configure `tcpborphserver3` to start on boot. The following file, saved as `/etc/init.d/tcpborphserver3` is one way to do this:
  ```
  #!/bin/sh
  ### BEGIN INIT INFO
  # Provides:          tcpborphserver
  # Required-Start:    $remote_fs $syslog $network
  # Required-Stop:     $remote_fs $syslog $network
  # Default-Start:     2 3 4 5
  # Default-Stop:      0 1 6
  # Short-Description: Start daemon at boot time
  # Description:       Enable service provided by daemon.
  ### END INIT INFO
  
  bofdir="/boffiles"
  user="root"
  cmd="/usr/local/sbin/tcpborphserver3 -l /dev/null -b $bofdir"
  
  name=`basename $0`
  pid_file="/var/run/$name.pid"
  stdout_log="/var/log/$name.log"
  stderr_log="/var/log/$name.err"
  
  get_pid() {
      cat "$pid_file"
  }
  
  is_running() {
      [ -f "$pid_file" ] && ps `get_pid` > /dev/null 2>&1
  }
  
  case "$1" in
      start)
      if is_running; then
          echo "Already started"
      else
          echo "Starting $name"
          sudo -u "$user" $cmd >> "$stdout_log" 2>> "$stderr_log"
          PID=`pgrep tcpborphserver3`
          echo $PID > "$pid_file"
          if ! is_running; then
              echo "Unable to start, see $stdout_log and $stderr_log"
              exit 1
          fi
      fi
      ;;
      stop)
      if is_running; then
          echo -n "Stopping $name.."
          kill `get_pid`
          for i in {1..10}
          do
              if ! is_running; then
                  break
              fi
  
              echo -n "."
              sleep 1
          done
          echo
  
          if is_running; then
              echo "Not stopped; may still be shutting down or shutdown may have failed"
              exit 1
          else
              echo "Stopped"
              if [ -f "$pid_file" ]; then
                  rm "$pid_file"
              fi
          fi
      else
          echo "Not running"
      fi
      ;;
      restart)
      $0 stop
      if is_running; then
          echo "Unable to stop, will not attempt to start"
          exit 1
      fi
      $0 start
      ;;
      status)
      if is_running; then
          echo "Running"
      else
          echo "Stopped"
          exit 1
      fi
      ;;
      *)
      echo "Usage: $0 {start|stop|restart|status}"
      exit 1
      ;;
  esac
  
  exit 0
  ```

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
