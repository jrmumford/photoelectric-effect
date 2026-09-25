# Photoelectric Effect (Python)

A Python replacement for the LabVIEW 2012 program `Photoelectric_Effect_v6.vi`.
It talks to the same LabJack U6 inside the apparatus, shows the same three
experiments, and reads and writes the same data files.

Download the latest version from the repository's **Releases** page (on the
right-hand side of the GitHub repository page).

## Installing on Windows (Windows 10 or 11, 64-bit)

1. Install the LabJack driver once per PC. Download the Windows installer from
   labjack.com (Support → Software & Driver → Installer Downloads) and run it.
   The Photoelectric Effect installer reminds you if it's missing.
2. Run `PhotoelectricEffect-Setup-<version>.exe`. Windows SmartScreen may warn
   that the publisher is unknown; click **More info → Run anyway**.
3. Start the program from the Start Menu. The Start Menu also has a
   **Simulator** shortcut and a **Check LabJack Connection** shortcut.

## Installing on Macs (Intel or Apple Silicon, macOS 12 or newer)

1. Download `PhotoelectricEffect-<version>-mac.dmg`, open it, and drag the app into
   Applications. It's a universal app, so the same file runs natively on both
   kinds of Mac. The LabJack driver is inside the app, so there's nothing else
   to install.
2. On first launch macOS blocks the app because it isn't signed with an Apple
   Developer ID. Open **System Settings → Privacy & Security**, scroll down, and
   click **Open Anyway**. You only need to do this once per Mac. Alternatively,
   run this in Terminal:
   `xattr -dr com.apple.quarantine "/Applications/Photoelectric Effect.app"`

To check a computer's hardware setup without opening the window:
`"/Applications/Photoelectric Effect.app/Contents/MacOS/Photoelectric Effect" --check-hardware`

### Rebuilding the Mac app

Build on an Apple Silicon Mac with conda (miniconda or miniforge) and Rosetta
(`sudo softwareupdate --install-rosetta --agree-to-license`):

```bash
sh packaging/build_mac.sh    # writes dist/Photoelectric Effect.app and .dmg
```

numpy and matplotlib don't publish universal packages, so the script builds the
app twice from pinned conda-forge environments, one per architecture. It then
combines each pair of binaries with `packaging/merge_universal.py`. The first
run creates the environments in `build/` (a few minutes); later runs reuse
them. To change a package version, edit `PACKAGES` in the script and delete
`build/`.

## Making a release

GitHub builds the Windows installer automatically
(`.github/workflows/build.yml`). The Mac app is built locally, since the
universal build needs an Apple Silicon Mac with Rosetta.

1. Set the new version in `photoelectric/__init__.py` (for example `1.0.1`) and commit.
2. Tag and push. This builds the Windows installer and creates the release:
   ```bash
   git tag v1.0.1
   git push origin main v1.0.1
   ```
3. Build the Mac app and add it to the same release:
   ```bash
   sh packaging/build_mac.sh
   cp "dist/Photoelectric Effect.dmg" dist/PhotoelectricEffect-1.0.1-mac.dmg
   gh release upload v1.0.1 dist/PhotoelectricEffect-1.0.1-mac.dmg
   ```

Every push to `main` also builds the Windows installer and runs the tests on
Windows, macOS and Linux. The installer is attached to the run under
**Actions → the run → Artifacts**.

## Running from source

```bash
pip install -r requirements.txt
python -m photoelectric                   # with the apparatus plugged in
python -m photoelectric --simulate        # no hardware: switches and bias knob are on screen
python -m photoelectric --check-hardware  # print one reading and exit
```

From source, the LabJack driver is found automatically in `drivers/macos/`.
To install it system-wide instead, run `sudo sh drivers/macos/install.sh`.
LabJack's own macOS installers don't provide a usable driver on Apple Silicon:
the LJM installer doesn't include the Exodriver, and its libusb is Intel-only.
The 2013 `Exodriver_NativeUSB_Setup_MacOSX.zip` is Intel-only too.

- **Windows:** the LabJack UD driver, from a current installer on labjack.com
- **Linux:** build the Exodriver from github.com/labjack/exodriver

## What it does

| Tab | Controls |
|---|---|
| Stopping Potential vs. Frequency | Record, Clear Last, Clear All, Calculate Slope (least-squares fit), Calculate Planck's Constant (h = −e × slope), Save / Read data file |
| Stopping Potential vs. Intensity | Record, Clear Last, Clear All |
| PhotoCurrent vs. Bias Voltage | Begin / End Recording (adds a point whenever the reading changes), Clear All |

The live readouts across the top show the bias voltage, the photocurrent, the
selected LED (name, color, frequency) and the intensity bar.

## Hardware mapping (taken from the original VIs)

| LabJack U6 input | Signal |
|---|---|
| AIN0 | Photocurrent: 1 V reads as 1 nA |
| AIN1 | Bias voltage (V) |
| AIN2 | Color switch: 10-position voltage ladder, 0 V (OFF) to 3.22 V (624 nm) |
| AIN3 | Intensity switch: positions 1 to 4 are intensities 1 to 4, all others are OFF |

Each channel is read single-ended at ±10 V. Each reading averages 10
samples. Photocurrent and bias voltage are rounded to 0.001.

## Layout

- `photoelectric/physics.py`: constants, switch decoding, LED table
- `photoelectric/data.py`: recording, linear fit, Planck's constant, file format
- `photoelectric/daq.py`: LabJack U6 reader and simulator
- `photoelectric/gui.py`: Tkinter/matplotlib window
- `drivers/macos/`: LabJack Exodriver 2.7.0 and libusb, universal (Intel + Apple Silicon)
- `packaging/`: PyInstaller specs, Mac build and merge scripts, Windows installer script, icons
- `.github/workflows/build.yml`: tests plus Windows build on GitHub Actions
- `tests/`: run with `pytest`

## Differences from the LabVIEW version

- Recording a stopping potential against frequency with the LED off is refused.
  LabVIEW recorded an infinite frequency in that case.
- Clear All Data (frequency tab) also removes the old best-fit line from saved files.
- Saved values use 8 decimal places. v6 used 3. Files from either version open fine.
- `--simulate` mode is new.
