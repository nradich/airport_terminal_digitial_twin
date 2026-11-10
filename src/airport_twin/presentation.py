"""Pure Python presentation data; no Spark, MLflow, USD or Kit imports."""

from __future__ import annotations

import math

from airport_twin.layout import shape

METRICS = ("peak_pax_A4", "gates_in_crit", "avg_co2", "security_queue_p95")


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


def legend_data(thresholds: list, palette: list[dict]) -> dict:
    """Validate governed threshold/palette snapshots and describe inclusive edges."""
    if {row["status"] for row in palette} != {"ok", "warn", "crit"} or len(palette) != 3:
        raise ValueError("Legend requires all three governed statuses")
    limits, seen = [], set()
    for asset_type, metric, warn, crit in sorted(thresholds):
        if not all(math.isfinite(float(v)) for v in (warn, crit)) or warn >= crit:
            raise ValueError("Invalid legend threshold")
        if (asset_type, metric) in seen:
            raise ValueError("Duplicate legend threshold")
        seen.add((asset_type, metric))
        limits.append(
            {
                "asset_type": asset_type,
                "metric": metric,
                "warn": float(warn),
                "crit": float(crit),
                "text": f"{asset_type} · {metric}: warn ≥ {warn:g}, crit ≥ {crit:g}",
            }
        )
    colours = {row["status"]: row["colour"] for row in palette}
    if any(len(c) != 7 or not c.startswith("#") for c in colours.values()):
        raise ValueError("Invalid governed colour")
    return {
        "colours": colours,
        "thresholds": limits,
        "categorical": ["bridge fault → crit", "flight delayed → warn"],
    }


def metric_values(histories: dict[str, list[dict]], step: int) -> dict[str, float]:
    """Require actual logged values at this exact step, without interpolation/fill."""
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError("Invalid simulation step")
    result = {}
    for key in METRICS:
        matches = [row for row in histories.get(key, []) if row["step"] == step]
        if len(matches) != 1 or not math.isfinite(float(matches[0]["value"])):
            raise ValueError(f"Missing, duplicate or invalid MLflow metric {key} at step {step}")
        result[key] = float(matches[0]["value"])
    return result


def run_panel_data(run: dict, step: int) -> dict:
    """Film-friendly labels with exact metric keys retained in the payload."""
    values = metric_values(run["metric_history"], step)
    return {
        "title": f"{run['scenario']} · {run['run_name']}",
        "identity": f"Run {run['run_id'][:8]} · minute {step}",
        "url": run["run_url"],
        "metrics": values,
        "metric_text": [
            f"A4 peak: {values['peak_pax_A4']:.0f} people",
            f"Critical gates: {values['gates_in_crit']:.0f}",
            f"Average CO₂: {values['avg_co2']:.0f} ppm",
            f"Security queue p95: {values['security_queue_p95']:.1f}",
        ],
    }
