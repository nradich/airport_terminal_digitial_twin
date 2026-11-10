"""Historical state uses the same governed SQL templates as the state views."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4


def timeline_frames(platform, run_id: str) -> tuple[list[dict], dict[str, int]]:
    """Read one run from UC sensor_readings and score every minute in Spark SQL."""
    from airport_twin.data import render, sql_text
    from airport_twin.sim import validate_readings
    from airport_twin.tracking import assert_run

    run = assert_run(platform.config, run_id)
    versions = platform.versions()
    readings = platform.spark.read.option("versionAsOf", versions["sensor_readings"]).table(
        platform.config.table("sensor_readings")
    )
    readings = readings.where(readings.run_id == run_id)
    validate_readings([tuple(row) for row in readings.collect()])
    source, scored = "replay_" + uuid4().hex, "scored_" + uuid4().hex
    readings.createOrReplaceTempView(source)
    values = {
        "namespace": platform.config.namespace,
        "readings": source,
        "time_partition": ", ts",
        "time_column": ", ts",
        "state_source": scored,
        "colour_expression": sql_text("colour.sql"),
    }
    try:
        state = platform.spark.sql(render(sql_text("latest_state.sql"), values))
        state.createOrReplaceTempView(scored)
        metrics = [row.asDict() for row in state.collect()]
        gates = [
            row.asDict()
            for row in platform.spark.sql(render(sql_text("gate_health.sql"), values)).collect()
        ]
    finally:
        platform.spark.catalog.dropTempView(scored)
        platform.spark.catalog.dropTempView(source)
    if versions != platform.versions():
        raise RuntimeError("Sources changed while reading replay; retry preparation")
    start = datetime.fromisoformat(run.data.params["start_utc"]).replace(tzinfo=None)
    frames = assemble_frames(metrics, gates, start, int(run.data.params["minutes"]))
    return frames, versions


def assemble_frames(
    metrics: list[dict], gates: list[dict], start: datetime, minutes: int
) -> list[dict]:
    """Reject incomplete/off-grid history instead of displaying stale samples."""
    groups: dict[datetime, list[dict]] = {}
    scores: dict[datetime, list[dict]] = {}
    for row in metrics:
        groups.setdefault(row["ts"], []).append(row)
    for row in gates:
        scores.setdefault(row["ts"], []).append(row)
    expected = {start + timedelta(minutes=i) for i in range(minutes)}
    if set(groups) != expected or set(scores) != expected:
        raise ValueError("Replay timestamps are incomplete or off the one-minute grid")
    frames = []
    for step, stamp in enumerate(sorted(expected)):
        rows = groups[stamp]
        states = scores[stamp] + [row for row in rows if row["asset_type"] != "gate"]
        if len(rows) != 42 or len(states) != 10 or len({r["asset_id"] for r in states}) != 10:
            raise ValueError("Replay frame has missing/duplicate assets or metrics")
        if any(
            row.get("status") not in {"ok", "warn", "crit"} or not row.get("colour")
            for row in rows + states
        ):
            raise ValueError("Replay contains invalid governed severity")
        frames.append(
            {
                "step": step,
                "ts": stamp.isoformat(),
                "states": sorted(states, key=lambda row: row["asset_id"]),
            }
        )
    return frames
