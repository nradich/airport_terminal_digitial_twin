from datetime import datetime, timedelta

import pytest

from airport_twin.timeline import assemble_frames


def test_historical_frames_reject_off_grid_and_incomplete_state():
    start = datetime(2026, 11, 9, 22)
    gate = [
        {
            "asset_id": f"GATE_A{i}",
            "asset_type": "gate",
            "ts": start,
            "status": "ok",
            "colour": "#22C55E",
        }
        for i in range(1, 9)
    ]
    shared = [
        {
            "asset_id": name,
            "asset_type": name.lower(),
            "ts": start,
            "status": "ok",
            "colour": "#22C55E",
        }
        for name in ("SECURITY", "BAGGAGE")
    ]
    readings = [dict(row) for row in gate for _ in range(5)] + shared
    frames = assemble_frames(readings, gate, start, 1)
    assert frames[0]["step"] == 0 and len(frames[0]["states"]) == 10
    with pytest.raises(ValueError, match="missing"):
        assemble_frames(readings[:-1], gate, start, 1)
    with pytest.raises(ValueError, match="one-minute"):
        assemble_frames(readings, gate, start + timedelta(seconds=1), 1)
    readings[0]["status"] = None
    with pytest.raises(ValueError, match="severity"):
        assemble_frames(readings, gate, start, 1)
