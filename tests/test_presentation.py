import pytest

from airport_twin.data import ASSET_NAMES, ASSETS
from airport_twin.presentation import (
    METRICS,
    asset_labels,
    legend_data,
    metric_values,
    run_panel_data,
)


def named_assets():
    keys = ("asset_id", "asset_type", "zone", "prim_path", "display_name")
    return [dict(zip(keys, row, strict=True), asset_name=ASSET_NAMES[row[0]]) for row in ASSETS]


def test_labels_use_governed_names_and_roof_anchors():
    assets = named_assets()
    assets[3]["asset_name"] = "A4 — delayed flight"
    labels = {row["asset_id"]: row for row in asset_labels(assets)}
    assert len(labels) == 10
    assert labels["GATE_A4"]["text"] == "A4 — delayed flight"
    assert labels["GATE_A4"]["anchor"] == [42.0, 10.0, 4.2]
    assert labels["SECURITY"]["text"] == "Security"
    assert labels["BAGGAGE"]["text"] == "Baggage"
    assert labels["GATE_A4"]["prim_path"] == "/World/Concourse_A/Gate_A4"


def test_labels_reject_missing_and_duplicate_assets():
    assets = named_assets()
    with pytest.raises(ValueError, match="Duplicate"):
        asset_labels(assets + [assets[0]])
    assets[0]["asset_name"] = " "
    with pytest.raises(ValueError, match="asset_name"):
        asset_labels(assets)


def test_legend_uses_supplied_governed_palette_and_inclusive_thresholds():
    palette = [
        {"status": status, "colour": colour}
        for status, colour in (("ok", "#00AA00"), ("warn", "#EEEE00"), ("crit", "#DD0000"))
    ]
    legend = legend_data([("gate", "pax_count", 120.0, 180.0)], palette)
    assert legend["colours"]["warn"] == "#EEEE00"
    assert legend["thresholds"][0]["text"].endswith("warn ≥ 120, crit ≥ 180")
    assert "bridge fault → crit" in legend["categorical"]
    with pytest.raises(ValueError, match="threshold"):
        legend_data([("gate", "pax_count", float("nan"), 180.0)], palette)
    with pytest.raises(ValueError, match="Duplicate"):
        legend_data([("gate", "pax_count", 1, 2)] * 2, palette)
    with pytest.raises(ValueError, match="three"):
        legend_data([], palette[:2])


def test_panel_uses_exact_mlflow_step_and_run_identity():
    histories = {key: [{"step": 0, "value": 1}, {"step": 1, "value": 5}] for key in METRICS}
    run = {
        "scenario": "delay_A4",
        "run_name": "Delay film take",
        "run_id": "abc12345rest",
        "run_url": "http://localhost:5000/mlflow/#/experiments/5/runs/abc12345rest",
        "metric_history": histories,
    }
    panel = run_panel_data(run, 0)
    assert panel["metrics"]["peak_pax_A4"] == 1
    assert "abc12345" in panel["identity"] and "minute 0" in panel["identity"]
    assert "Delay film take" in panel["title"]
    assert metric_values(histories, 1)["avg_co2"] == 5
    with pytest.raises(ValueError, match="Missing"):
        metric_values(histories, 2)
    histories["avg_co2"].append({"step": 0, "value": 9})
    with pytest.raises(ValueError, match="duplicate"):
        metric_values(histories, 0)
