import pytest

from airport_twin.data import ASSET_NAMES, ASSETS
from airport_twin.presentation import asset_labels


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
