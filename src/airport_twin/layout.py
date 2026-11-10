"""One geometry layout shared by OpenUSD and the top-down heatmap."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Shape:
    position: tuple[float, float, float]
    size: tuple[float, float, float]
    cylinder: bool = False


FLOOR = Shape((21.0, 0.0, -0.25), (60.0, 15.0, 0.5))
CAMERAS = (
    ("Overview", "Overview", (21, -45, 65), (21, 0, 1), "orthographic"),
    ("A4CloseUp", "Gate A4 close-up", (53, -7, 18.5), (42, 10, 2), "perspective"),
)


def shape(asset: dict) -> Shape:
    if asset["asset_type"] == "gate":
        index = int(asset["asset_id"].removeprefix("GATE_A")) - 1
        if not 0 <= index < 8:
            raise ValueError("Unknown gate layout")
        return Shape((float((index % 4) * 14), 10.0 if index < 4 else -10.0, 1.5), (8.0, 6.0, 3.0))
    if asset["asset_type"] == "security":
        return Shape((-14.0, 0.0, 1.5), (8.0, 8.0, 3.0), True)
    if asset["asset_type"] == "baggage":
        return Shape((56.0, 0.0, 1.5), (8.0, 8.0, 3.0))
    raise ValueError(f"Unknown asset type: {asset['asset_type']}")
