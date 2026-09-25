from pathlib import Path

import pytest

from photoelectric.data import Experiment, Sample
from photoelectric.daq import SimulatedApparatus
from photoelectric.physics import (
    SWITCH_VOLTS,
    intensity_for_position,
    led_for_position,
    round_thousandth,
    switch_position,
)

LEGACY_FILE = Path(__file__).parent / "data" / "labview_v5_sample.txt"  # saved by the LabVIEW program


def test_switch_positions_at_nominal_voltages():
    for pos, volts in enumerate(SWITCH_VOLTS[:10]):
        assert switch_position(volts) == pos


def test_switch_position_thresholds_are_midpoints():
    assert switch_position(0.414) == 0
    assert switch_position(0.416) == 1
    assert switch_position(3.35) == 9
    assert switch_position(-1.5) == 0
    assert switch_position(4.5) == 0


def test_intensity_mapping():
    assert [intensity_for_position(p) for p in range(10)] == [0, 1, 2, 3, 4, 0, 0, 0, 0, 0]


def test_led_frequencies_match_legacy_file():
    # Frequencies written by the LabVIEW program for 624, 590, 525, 505, 470, 400 nm.
    expected = {9: 480437500000000.0, 7: 508123728813559.312, 6: 571034285714285.75,
                5: 593649504950495.0, 4: 637857446808510.625, 2: 749482500000000.0}
    for pos, f in expected.items():
        assert led_for_position(pos).frequency_hz == pytest.approx(f, rel=1e-12)
    assert led_for_position(0).frequency_hz is None


def test_round_thousandth():
    assert round_thousandth(-0.37254745) == -0.373
    assert round_thousandth(0.0004) == 0.0


def s(i=0.0, v=-1.0, f=5e14, n=4):
    return Sample(i, v, f, n)


def test_record_fit_and_planck():
    e = Experiment()
    for f, v in [(4.8e14, -0.4), (6.0e14, -0.9), (7.5e14, -1.525)]:
        e.record_vs_frequency(s(v=v, f=f))
    e.calculate_slope()
    assert e.slope == pytest.approx(-4.1667e-15, rel=1e-3)
    assert len(e.fit_voltage) == 3
    e.calculate_planck()
    assert e.planck == pytest.approx(6.675e-34, rel=1e-3)
    e.clear_last_frequency()
    assert len(e.vs_frequency) == 2 and e.fit_voltage == []
    e.clear_all_frequency()
    assert len(e.vs_frequency) == 0 and e.slope is None


def test_cannot_record_frequency_with_led_off():
    with pytest.raises(ValueError):
        Experiment().record_vs_frequency(s(f=None))


def test_slope_needs_two_frequencies():
    e = Experiment()
    e.record_vs_frequency(s())
    e.record_vs_frequency(s())
    with pytest.raises(ValueError):
        e.calculate_slope()


def test_iv_records_only_changes_while_recording():
    e = Experiment()
    assert not e.update_iv(s(v=0.1), s(v=0.2))
    e.begin_iv()
    assert not e.update_iv(None, s(v=0.2))
    assert not e.update_iv(s(v=0.2), s(v=0.2))
    assert e.update_iv(s(v=0.2), s(v=0.3))
    assert e.iv_curve.voltage == [0.3]
    e.clear_iv()
    assert not e.recording_iv and len(e.iv_curve) == 0


def test_save_load_roundtrip(tmp_path):
    e = Experiment()
    for f, v in [(4.8e14, -0.4), (6.0e14, -0.9), (7.5e14, -1.5)]:
        e.record_vs_frequency(s(v=v, f=f))
    e.record_vs_intensity(s(v=-0.8, n=2))
    e.begin_iv()
    e.update_iv(s(v=0), s(i=0.1, v=0.5))
    e.calculate_slope()
    path = tmp_path / "data.txt"
    e.save(str(path))
    assert len(path.read_text().splitlines()) == 17

    loaded = Experiment()
    loaded.load(str(path))
    assert loaded.vs_frequency.voltage == pytest.approx(e.vs_frequency.voltage)
    assert loaded.vs_frequency.frequency == pytest.approx(e.vs_frequency.frequency)
    assert loaded.vs_intensity.intensity == [2.0]
    assert loaded.iv_curve.photocurrent == pytest.approx([0.1])
    assert loaded.fit_voltage == pytest.approx(e.fit_voltage)


@pytest.mark.skipif(not LEGACY_FILE.exists(), reason="legacy sample file not present")
def test_loads_file_written_by_labview_program():
    e = Experiment()
    e.load(str(LEGACY_FILE))
    assert len(e.vs_frequency) == 6
    assert e.vs_frequency.voltage[0] == pytest.approx(-0.37254745)
    assert len(e.vs_intensity) == 0 and len(e.iv_curve) == 0
    assert len(e.fit_voltage) == 6
    e.calculate_slope()
    e.calculate_planck()
    assert 4e-34 < e.planck < 8e-34


def test_simulator_decodes_to_its_own_settings():
    sim = SimulatedApparatus()
    sim.set_controls(color_position=5, intensity_position=3, bias_voltage=-0.5)
    _, bias, color_v, intensity_v = sim.read()
    assert switch_position(color_v) == 5
    assert intensity_for_position(switch_position(intensity_v)) == 3
    assert bias == pytest.approx(-0.5, abs=0.01)
