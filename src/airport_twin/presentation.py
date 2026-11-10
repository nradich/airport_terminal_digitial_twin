"""Pure Python presentation data; no Spark, MLflow, USD or Kit imports."""

from __future__ import annotations

from airport_twin.layout import shape


def asset_labels(assets: list[dict]) -> list[dict]:
    """Build billboard anchors and governed names, never infer labels in Kit."""
    labels = []
    seen = set()
    for asset in sorted(assets, key=lambda a: a["asset_id"]):
        name = asset.get("asset_name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every asset needs a nonempty governed asset_name")
        if asset["asset_id"] in seen:
            raise ValueError("Duplicate asset label")
        seen.add(asset["asset_id"])
        layout = shape(asset)
        x, y, z = layout.position
        labels.append(
            {
                "asset_id": asset["asset_id"],
                "text": name.strip(),
                "prim_path": asset["prim_path"],
                "anchor": [x, y, z + layout.size[2] / 2 + 1.2],
            }
        )
    return labels
