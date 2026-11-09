from datetime import datetime

import pytest

from airport_twin.config import SimulationConfig
from airport_twin.sim import numeric_status, simulate, validate_readings


def test_deterministic_and_filmable():
    base = simulate(SimulationConfig(), "run")
    assert base == simulate(SimulationConfig(), "run")
    delay = simulate(SimulationConfig(scenario="delay_A4"), "run")
    assert len(base.readings) == len(delay.readings) == 2520
    assert len(base.flights) == 8
    assert delay.metrics[-1]["peak_pax_A4"] > base.metrics[-1]["peak_pax_A4"]
    last = {r[0]: r[3] for r in delay.readings[-42:] if r[2] == "pax_count"}
    assert last["GATE_A4"] >= 180
    assert base.metrics[-1]["gates_in_crit"] == 0


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "ok"), (119.99, "ok"), (120, "warn"), (179.99, "warn"), (180, "crit")],
)
def test_status_edges(value, expected):
    assert numeric_status(value, 120, 180) == expected


@pytest.mark.parametrize(
    ("metric", "num", "text"),
    [
        ("pax_count", None, None),
        ("pax_count", 1.0, "one"),
        ("pax_count", float("nan"), None),
        ("pax_count", float("inf"), None),
        ("flight_status", 1.0, None),
        ("flight_status", None, "oops"),
        ("unknown", 1.0, None),
    ],
)
def test_invalid_readings(metric, num, text):
    with pytest.raises(ValueError):
        validate_readings([("GATE_A1", datetime(2026, 1, 1), metric, num, text, "run")])


def test_duplicate_readings():
    row = ("GATE_A1", datetime(2026, 1, 1), "pax_count", 1.0, None, "run")
    with pytest.raises(ValueError, match="Duplicate"):
        validate_readings([row, row])
