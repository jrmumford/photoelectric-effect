#!/bin/sh
# Installs the LabJack Exodriver system-wide on macOS (Intel and Apple Silicon).
# Only needed when running from source; the packaged app has its own copy.
#
# liblabjackusb 2.7.0 built from github.com/labjack/exodriver against libusb
# from conda-forge, as universal (x86_64 + arm64) binaries. libusb has its own
# name so LabJack's installer copy in /usr/local/lib is left alone.
#
# Usage:  sudo sh install.sh
set -e
cd "$(dirname "$0")"
mkdir -p /usr/local/lib
cp libusb-1.0.0-exodriver.dylib liblabjackusb-2.7.0.dylib /usr/local/lib/
ln -sf /usr/local/lib/liblabjackusb-2.7.0.dylib /usr/local/lib/liblabjackusb.dylib
echo "Installed. Unplug and replug the LabJack."
