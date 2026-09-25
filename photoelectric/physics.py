"""Apparatus constants and signal decoding.

Ported from the LabVIEW subVIs Obtain_Switch_Position.vi,
Get_Color_From_SwitchPosition.vi, Get_Intensity_From_SwitchPosition.vi and
Round_to_Thousandth.vi. All numeric constants are the ones found in those VIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Constants exactly as they appear on the original block diagrams.
SPEED_OF_LIGHT_NM_PER_S = 2.99793e17
ELEMENTARY_CHARGE_C = 1.602e-19

# Voltage produced by the 10-position rotary switches at positions 0..9.
# The last two entries are sentinels, so the search below always ends.
SWITCH_VOLTS = (0.0, 0.83, 1.43, 1.874, 2.22, 2.489, 2.725, 2.905, 3.077, 3.22, 3.5, 5.0)


@dataclass(frozen=True)
class LED:
    name: str
    wavelength_nm: Optional[float]  # None when the LED is off
    color: str  # display color used by the original front panel

    @property
    def frequency_hz(self) -> Optional[float]:
        if not self.wavelength_nm:
            return None
        return SPEED_OF_LIGHT_NM_PER_S / self.wavelength_nm


# Indexed by switch position.
LEDS = (
    LED("OFF", None, "#FFFFFF"),
    LED("380 nm UV", 380, "#FF96FF"),
    LED("400 nm Purple/UV", 400, "#C753D7"),
    LED("460 nm Violet", 460, "#D700FF"),
    LED("470 nm Blue", 470, "#5A59FF"),
    LED("505 nm Lt Green", 505, "#12FF75"),
    LED("525 nm Green", 525, "#35FF00"),
    LED("590 nm Yellow", 590, "#F7C109"),
    LED("605 nm Orange", 605, "#FB4204"),
    LED("624 nm Red", 624, "#FF0000"),
)

INTENSITY_LABELS = ("OFF", "1 (Low)", "2", "3", "4 (High)")
MAX_INTENSITY = 4


def switch_position(volts: float) -> int:
    """Convert a rotary-switch voltage (0 V to 3.22 V) to a position from 0 to 9.

    Walks the voltage table and stops at the first position whose midpoint
    to the next position is above the reading. Readings outside -1 V to 4 V
    count as position 0 (OFF), the same as the original.
    """
    if volts < -1 or volts > 4:
        return 0
    for i in range(len(SWITCH_VOLTS) - 1):
        if volts < (SWITCH_VOLTS[i] + SWITCH_VOLTS[i + 1]) / 2:
            return min(i, len(LEDS) - 1)
    return len(LEDS) - 1


def led_for_position(position: int) -> LED:
    return LEDS[position] if 0 <= position < len(LEDS) else LEDS[0]


def intensity_for_position(position: int) -> int:
    """Switch positions 1-4 are intensities 1-4. Every other position is OFF (0)."""
    return position if 1 <= position <= MAX_INTENSITY else 0


def round_thousandth(x: float) -> float:
    # Python's round() rounds half to even, the same as LabVIEW's "Round To Nearest".
    return round(x * 1000) / 1000
