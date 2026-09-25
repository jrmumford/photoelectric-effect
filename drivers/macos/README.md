# LabJack Exodriver for macOS (universal)

These are prebuilt universal (x86_64 + arm64) binaries, macOS 12 or newer.
The Mac app bundles them. `install.sh` installs them system-wide for running
from source.

| File | Project | Version | License |
|---|---|---|---|
| `liblabjackusb-2.7.0.dylib` | [labjack/exodriver](https://github.com/labjack/exodriver) | 2.7.0 | MIT X11 (`LICENSE-exodriver.txt`) |
| `libusb-1.0.0-exodriver.dylib` | [libusb](https://github.com/libusb/libusb), via conda-forge | 1.0.29 | LGPL-2.1 (`LICENSE-libusb.txt`) |

libusb is unmodified. Only its file name and install name were changed, so it
can sit next to other copies of libusb. The source is at
https://github.com/libusb/libusb/releases/tag/v1.0.29. You can replace it with
any compatible libusb 1.0 build.

## Rebuilding

With arm64 and x86_64 builds of libusb (for example from conda-forge,
`osx-arm64` and `osx-64`):

```bash
lipo -create ARM64/libusb-1.0.0.dylib X86_64/libusb-1.0.0.dylib -output libusb-1.0.0-exodriver.dylib
install_name_tool -id @loader_path/libusb-1.0.0-exodriver.dylib libusb-1.0.0-exodriver.dylib
clang -arch arm64 -arch x86_64 -mmacosx-version-min=12.0 -dynamiclib -O2 -I ARM64/include/libusb-1.0 \
    exodriver/liblabjackusb/labjackusb.c ./libusb-1.0.0-exodriver.dylib \
    -install_name @loader_path/liblabjackusb-2.7.0.dylib -o liblabjackusb-2.7.0.dylib
codesign -f -s - libusb-1.0.0-exodriver.dylib liblabjackusb-2.7.0.dylib
```
