"""Experiment data model: recording, clearing, fitting, saving and loading.

Ported from the event cases of Photoelectric_Effect_v6.vi and from
Plot_Data_When_Flag_Set.vi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .physics import ELEMENTARY_CHARGE_C


@dataclass(frozen=True)
class Sample:
    """One reading of the apparatus, after rounding and switch decoding."""

    photocurrent_na: float
    voltage_v: float
    frequency_hz: Optional[float]  # None when the LED is off
    intensity: int


@dataclass
class Series:
    """A list of recorded samples. Each graph in the program has one."""

    photocurrent: List[float] = field(default_factory=list)
    voltage: List[float] = field(default_factory=list)
    frequency: List[float] = field(default_factory=list)
    intensity: List[float] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.voltage)

    def append(self, s: Sample) -> None:
        self.photocurrent.append(s.photocurrent_na)
        self.voltage.append(s.voltage_v)
        self.frequency.append(s.frequency_hz if s.frequency_hz is not None else 0.0)
        self.intensity.append(s.intensity)

    def pop(self) -> bool:
        if not self:
            return False
        for column in self._columns():
            column.pop()
        return True

    def clear(self) -> None:
        for column in self._columns():
            column.clear()

    def _columns(self):
        return (self.photocurrent, self.voltage, self.frequency, self.intensity)

    def _rows(self) -> List[List[float]]:
        return [list(c) for c in self._columns()] + [[len(self)]]

    @classmethod
    def _from_rows(cls, rows: List[np.ndarray]) -> "Series":
        n = int(rows[4][0]) if len(rows[4]) else 0
        return cls(*(list(map(float, r[:n])) for r in rows[:4]))


class Experiment:
    def __init__(self) -> None:
        self.vs_frequency = Series()
        self.vs_intensity = Series()
        self.iv_curve = Series()
        self.fit_frequency: List[float] = []
        self.fit_voltage: List[float] = []
        self.slope: Optional[float] = None
        self.intercept: Optional[float] = None
        self.planck: Optional[float] = None
        self.recording_iv = False

    # --- Stopping potential vs. frequency ----------------------------------

    def record_vs_frequency(self, s: Sample) -> None:
        if s.frequency_hz is None:
            raise ValueError("The LED is off. Choose a color before recording.")
        self.vs_frequency.append(s)

    def clear_last_frequency(self) -> None:
        if self.vs_frequency.pop():
            self._clear_fit_line()

    def clear_all_frequency(self) -> None:
        self.vs_frequency.clear()
        self._clear_fit_line()
        self.slope = self.intercept = self.planck = None

    def calculate_slope(self) -> None:
        x = np.asarray(self.vs_frequency.frequency)
        y = np.asarray(self.vs_frequency.voltage)
        if len(x) < 2 or np.ptp(x) == 0:
            raise ValueError("You need at least two data points at different frequencies.")
        self.slope, self.intercept = (float(v) for v in np.polyfit(x, y, 1))
        self.fit_frequency = list(x)
        self.fit_voltage = list(self.slope * x + self.intercept)
        self.planck = None

    def calculate_planck(self) -> None:
        if self.slope is None:
            raise ValueError("Calculate the slope first.")
        # Stopping potentials are negative, so the slope is negative and h = -e * slope.
        self.planck = self.slope * -ELEMENTARY_CHARGE_C

    def _clear_fit_line(self) -> None:
        self.fit_frequency = []
        self.fit_voltage = []

    # --- Stopping potential vs. intensity ----------------------------------

    def record_vs_intensity(self, s: Sample) -> None:
        self.vs_intensity.append(s)

    def clear_last_intensity(self) -> None:
        self.vs_intensity.pop()

    def clear_all_intensity(self) -> None:
        self.vs_intensity.clear()

    # --- Photocurrent vs. bias voltage -------------------------------------

    def begin_iv(self) -> None:
        self.recording_iv = True

    def end_iv(self) -> None:
        self.recording_iv = False

    def clear_iv(self) -> None:
        self.iv_curve.clear()
        self.recording_iv = False

    def update_iv(self, previous: Optional[Sample], current: Sample) -> bool:
        """Record a point on the I-V curve if recording is on and the reading changed."""
        if self.recording_iv and previous is not None and current != previous:
            self.iv_curve.append(current)
            return True
        return False

    # --- File I/O -----------------------------------------------------------
    #
    # Same tab-delimited layout the LabVIEW program used, so files from the
    # old program still open. Rows are padded with zeros to equal length:
    #   0-4    vs. frequency:  photocurrent, voltage, frequency, intensity, count
    #   5-9    vs. intensity:  (same five rows)
    #   10-14  I-V curve:      (same five rows)
    #   15     best-fit stopping potential
    #   16     best-fit LED frequency

    def save(self, path: str) -> None:
        rows = (
            self.vs_frequency._rows()
            + self.vs_intensity._rows()
            + self.iv_curve._rows()
            + [list(self.fit_voltage), list(self.fit_frequency)]
        )
        width = max(1, max(len(r) for r in rows))
        with open(path, "w", newline="") as f:
            for r in rows:
                padded = list(r) + [0.0] * (width - len(r))
                f.write("\t".join(f"{v:.8f}" for v in padded) + "\n")

    def load(self, path: str) -> None:
        rows = []
        with open(path) as f:
            for line in f:
                if line.strip():
                    rows.append(np.array([float(v) for v in line.split()]))
        if len(rows) < 17:
            raise ValueError(f"Expected 17 rows of data but found {len(rows)}.")

        vs_frequency = Series._from_rows(rows[0:5])
        n_fit = len(vs_frequency) if np.any(rows[15]) else 0

        self.vs_frequency = vs_frequency
        self.vs_intensity = Series._from_rows(rows[5:10])
        self.iv_curve = Series._from_rows(rows[10:15])
        self.fit_voltage = list(map(float, rows[15][:n_fit]))
        self.fit_frequency = list(map(float, rows[16][:n_fit]))
        self.recording_iv = False
