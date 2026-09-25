"""Data acquisition: the LabJack U6 (port of LabJack_Read.vi) plus a simulator.

Channel map (from Photoelectric_Effect_v6.vi):
    AIN0  photocurrent (1 V reads as 1 nA)
    AIN1  bias voltage (V)
    AIN2  wavelength (color) selector switch
    AIN3  intensity selector switch
"""

from __future__ import annotations

import ctypes
import math
import random
import sys
import threading
from pathlib import Path
from typing import Tuple

from .physics import ELEMENTARY_CHARGE_C, LEDS, SWITCH_VOLTS

Reading = Tuple[float, float, float, float]

NOT_CONNECTED_MESSAGE = (
    "Most likely, the Photoelectric Effect Apparatus needs to be plugged into "
    "USB Port of the computer.  Check the USB plug and relaunch the program."
)


class DAQError(Exception):
    pass


FROZEN = getattr(sys, "frozen", False)  # running inside the packaged app


def _bundled_driver_dirs():
    if FROZEN:
        yield Path(sys._MEIPASS)
    yield Path(__file__).resolve().parents[1] / "drivers" / "macos"


def _load_bundled_exodriver(LabJackPython) -> None:
    """Hand LabJackPython the Exodriver shipped with this program.

    LabJackPython only looks in /usr/local/lib. The packaged app always uses its
    own copy; from source it is the fallback when none is installed.
    """
    if sys.platform != "darwin":
        return
    for d in _bundled_driver_dirs():
        path = d / "liblabjackusb-2.7.0.dylib"
        if not path.exists():
            continue
        try:
            lib = ctypes.CDLL(str(path), use_errno=True)
        except OSError:
            continue
        lib.LJUSB_StreamTO.errcheck = LabJackPython.errcheck
        lib.LJUSB_Read.errcheck = LabJackPython.errcheck
        LabJackPython.staticLib = lib
        return


class LabJackU6:
    """Reads AIN0-AIN3 single-ended at +/-10 V, averaging 10 samples per channel."""

    CHANNELS = (0, 1, 2, 3)
    SAMPLES_PER_READ = 10
    GAIN_INDEX = 0  # +/-10 V (LJ_rgBIP10V)

    def __init__(self, resolution_index: int = 0, settling_factor: int = 0) -> None:
        try:
            import u6  # LabJackPython
        except ImportError as e:
            raise DAQError(
                "LabJackPython is not installed. Run:  pip install LabJackPython\n"
                "It also needs the LabJack driver (Exodriver on macOS/Linux, "
                "the UD driver on Windows)."
            ) from e
        import LabJackPython

        if FROZEN or LabJackPython.staticLib is None:
            _load_bundled_exodriver(LabJackPython)
        if LabJackPython.staticLib is None:
            raise DAQError(
                "The LabJack driver could not be loaded, so the apparatus can't be reached.\n\n"
                "To install it:\n"
                "  macOS: sudo sh drivers/macos/install.sh\n"
                "  Windows: the LabJack UD driver installer from labjack.com\n"
                "  Linux: build the Exodriver from github.com/labjack/exodriver"
            )
        try:
            self._device = u6.U6()
            self._device.getCalibrationData()
        except Exception as e:
            raise DAQError(NOT_CONNECTED_MESSAGE) from e
        self._resolution_index = resolution_index
        self._settling_factor = settling_factor

    def read(self) -> Reading:
        sums = [0.0] * len(self.CHANNELS)
        try:
            for _ in range(self.SAMPLES_PER_READ):
                for i, ch in enumerate(self.CHANNELS):
                    sums[i] += self._device.getAIN(
                        ch,
                        resolutionIndex=self._resolution_index,
                        gainIndex=self.GAIN_INDEX,
                        settlingFactor=self._settling_factor,
                        differential=False,
                    )
        except Exception as e:
            raise DAQError(f"Lost contact with the LabJack: {e}\n\n{NOT_CONNECTED_MESSAGE}") from e
        return tuple(s / self.SAMPLES_PER_READ for s in sums)  # type: ignore[return-value]

    def close(self) -> None:
        try:
            self._device.close()
        except Exception:
            pass


class SimulatedApparatus:
    """Fake apparatus so the program can be used or demonstrated without hardware.

    The switches and bias knob are set from the GUI. The photocurrent follows
    a simple photoelectric model with a 1.4 eV work function.
    """

    WORK_FUNCTION_EV = 1.4
    PLANCK = 6.626e-34
    NOISE_V = 0.0003

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.color_position = 7
        self.intensity_position = 4
        self.bias_voltage = 0.0

    def set_controls(self, color_position: int, intensity_position: int, bias_voltage: float) -> None:
        with self._lock:
            self.color_position = color_position
            self.intensity_position = intensity_position
            self.bias_voltage = bias_voltage

    def read(self) -> Reading:
        with self._lock:
            color, intensity, bias = self.color_position, self.intensity_position, self.bias_voltage
        freq = LEDS[color].frequency_hz
        level = intensity if 1 <= intensity <= 4 else 0
        current = 0.0
        if freq and level:
            stopping = -(self.PLANCK * freq / ELEMENTARY_CHARGE_C - self.WORK_FUNCTION_EV)
            if bias > stopping:
                current = 0.05 * level * (1 - math.exp(-(bias - stopping) / 0.4))

        def noisy(v: float) -> float:
            return v + random.gauss(0, self.NOISE_V)

        return (noisy(current), noisy(bias), noisy(SWITCH_VOLTS[color]), noisy(SWITCH_VOLTS[intensity]))

    def close(self) -> None:
        pass
