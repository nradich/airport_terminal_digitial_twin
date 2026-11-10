"""Pure Python presentation data; no Spark, MLflow, USD or Kit imports."""

from __future__ import annotations

import math

from airport_twin.layout import shape

METRICS = ("peak_pax_A4", "gates_in_crit", "avg_co2", "security_queue_p95")


def linear_rgb(colour: str) -> tuple[float, float, float]:
    """Convert governed sRGB hex to USD's linear display colour."""
    if len(colour) != 7 or not colour.startswith("#"):
        raise ValueError("Expected #RRGGBB colour")
    values = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values)


def interpolate_rgb(start: tuple, end: tuple, progress: float) -> tuple[float, float, float]:
    """Clamp time and interpolate linear RGB; invalid measurements fail loudly."""
    if (
        len(start) != 3
        or len(end) != 3
        or not all(math.isfinite(v) for v in (*start, *end, progress))
    ):
        raise ValueError("Interpolation requires finite RGB triples and progress")
    if any(not 0 <= value <= 1 for value in (*start, *end)):
        raise ValueError("RGB values must be in [0, 1]")
    t = max(0.0, min(1.0, progress))
    if t == 0:
        return tuple(start)
    if t == 1:
        return tuple(end)
    return tuple(a + (b - a) * t for a, b in zip(start, end, strict=True))


def ripple_progress(assets: list[dict], elapsed: float, duration: float = 1.5) -> dict[str, float]:
    """A4 starts first; the distance-staggered wave finishes within duration."""
    if not math.isfinite(elapsed) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid transition timing")
    positions = {a["asset_id"]: shape(a).position for a in assets}
    if "GATE_A4" not in positions:
        raise ValueError("Ripple requires A4")
    origin = positions["GATE_A4"]
    distances = {key: math.dist(point, origin) for key, point in positions.items()}
    maximum = max(distances.values()) or 1.0
    return {
        key: max(0.0, min(1.0, (elapsed / duration - 0.4 * value / maximum) / 0.6))
        for key, value in distances.items()
    }


def transition_colours(
    start: dict[str, tuple],
    states: list[dict],
    assets: list[dict],
    elapsed: float,
    duration: float = 1.5,
) -> dict[str, tuple]:
    """Ease the governed colour change, with a brief neutral ripple highlight."""
    progress = ripple_progress(assets, elapsed, duration)
    result = {}
    if set(start) != {state["asset_id"] for state in states} or set(start) != set(progress):
        raise ValueError("Transition assets differ")
    for state in states:
        key = state["asset_id"]
        t = progress[key]
        eased = t * t * (3 - 2 * t)
        colour = interpolate_rgb(start[key], linear_rgb(state["colour"]), eased)
        # The white glint is a presentation cue, never a change to governed severity.
        pulse = 0.18 * math.sin(math.pi * t) if 0 < t < 1 else 0.0
        result[key] = tuple(value + (1 - value) * pulse for value in colour)
    return result


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
