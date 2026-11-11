"""Version-pinned audited replay; publication files remain the source of identity."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from airport_twin.presentation import METRICS, metric_values
from airport_twin.readers import ReadError
from airport_twin.tracking import assert_run, client


def replay_sets(data, run_id: str) -> list[dict]:
    """Return only complete sets sharing source versions, thresholds and geometry."""
    run = assert_run(data.config, run_id)
    minutes = int(run.data.params["minutes"])
    groups: dict[str, dict] = {}
    for row in data.pushes():
        if row["run_id"] != run_id:
            continue
        publication = data.publication(row["push_id"])
        manifest = publication["manifest"]
        identity = {
            key: manifest[key]
            for key in ("delta_versions", "thresholds", "glb_sha256", "base_sha256")
        }
        identity["run_id"] = run_id
        identity["rule_id"] = manifest.get("rules", {}).get("rule_id", "legacy-unrecorded")
        identity["story_sha256"] = manifest.get("story_sha256")
        identity["publisher"] = manifest.get("publisher")
        identity["assets_sha256"] = hashlib.sha256(
            json.dumps(
                sorted(manifest["assets"], key=lambda r: r["asset_id"]), sort_keys=True
            ).encode()
        ).hexdigest()
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        group = groups.setdefault(
            key,
            {
                "replay_id": key,
                "run_id": run_id,
                "minutes": minutes,
                "start_ts": run.data.params["start_utc"],
                "identity": identity,
                "publications": {},
            },
        )
        group["publications"].setdefault(manifest["step"], publication)
    return [group for group in groups.values() if set(group["publications"]) == set(range(minutes))]


def timeline(data, run_id: str, replay_id: str, start_step: int, end_step: int) -> dict:
    """Bound SQL pages, then compare every computed state to its publication."""
    sets = replay_sets(data, run_id)
    replay = next((item for item in sets if item["replay_id"] == replay_id), None)
    if replay is None:
        raise ReadError("REPLAY_NOT_FOUND", status=404)
    if not 0 <= start_step < end_step <= replay["minutes"] or end_step - start_step > 60:
        raise ReadError("INVALID_STEP_RANGE", status=422)
    identity = replay["identity"]
    from airport_twin.rules import rule_snapshot

    if identity.get("rule_id", "legacy-unrecorded") not in {
        "legacy-unrecorded",
        rule_snapshot()["rule_id"],
    }:
        raise ReadError("AUDIT_RULE_UNAVAILABLE", status=410)
    start = datetime.fromisoformat(replay["start_ts"])
    parameters = {
        "run_id": run_id,
        "versions": identity["delta_versions"],
        "thresholds": identity["thresholds"],
        "start_ts": (start + timedelta(minutes=start_step)).isoformat(),
    }
    while True:
        parameters["end_ts"] = (start + timedelta(minutes=end_step)).isoformat()
        try:
            rows = data.sql.read("history", parameters)
            break
        except ReadError as error:
            if error.code != "READ_LIMIT_EXCEEDED" or end_step - start_step == 1:
                raise
            end_step = start_step + max(1, (end_step - start_step) // 2)
    histories = {
        key: [
            {"step": m.step, "value": m.value}
            for m in client(data.config).get_metric_history(run_id, key)
        ]
        for key in METRICS
    }
    groups: dict[int, list[dict]] = {}
    for row in rows:
        stamp = row["ts"] if isinstance(row["ts"], datetime) else datetime.fromisoformat(row["ts"])
        minute = (stamp - start).total_seconds() / 60
        if minute != int(minute):
            raise ReadError("AUDIT_OFF_GRID", status=409)
        groups.setdefault(int(minute), []).append(row)
    if set(groups) != set(range(start_step, end_step)):
        raise ReadError("AUDIT_INCOMPLETE", status=409)
    frames = []
    for step in range(start_step, end_step):
        publication = replay["publications"][step]
        computed = groups[step]

        def states(values):
            return sorted((r["asset_id"], r["status"], r["colour"]) for r in values)

        if len(computed) != 10 or states(computed) != states(publication["manifest"]["states"]):
            raise ReadError("AUDIT_STATE_MISMATCH", status=409)
        frames.append(
            {
                "step": step,
                "push_id": publication["audit"]["push_id"],
                "states": computed,
                "metrics": metric_values(histories, step),
                "image_type": publication["image_type"],
            }
        )
    current = sorted(
        tuple(r[k] for k in ("asset_type", "metric", "warn", "crit"))
        for r in data.sql.read("thresholds")
    )
    result = {
        "replay_id": replay_id,
        "run_id": run_id,
        "start_step": start_step,
        "end_step": end_step,
        "next_step": end_step if end_step < replay["minutes"] else None,
        "sql_rows": len(rows),
        "metric_points": len(frames) * len(METRICS),
        "thresholds_changed": current != sorted(tuple(r) for r in identity["thresholds"]),
        "source_versions": identity["delta_versions"],
        "frames": frames,
    }
    encoded = json.dumps(result, default=lambda value: value.isoformat()).encode()
    if len(encoded) > 2 * 1024 * 1024:
        if end_step - start_step == 1:
            raise ReadError("READ_LIMIT_EXCEEDED", "Single step exceeds byte limit", 422)
        return timeline(
            data, run_id, replay_id, start_step, start_step + max(1, (end_step - start_step) // 2)
        )
    result["serialized_bytes"] = len(encoded)
    return result
