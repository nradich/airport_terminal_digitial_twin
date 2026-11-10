"""Explain a gate using immutable publication evidence and version-pinned SQL."""

from __future__ import annotations

from datetime import datetime, timedelta

from airport_twin.readers import ReadError
from airport_twin.rules import rule_snapshot
from airport_twin.tracking import run_url


def explain(rows: list[dict]) -> str:
    """Explain the worst governed severity without implementing colour logic again."""
    expected = {"pax_count", "hvac_temp_c", "co2_ppm", "jet_bridge_status", "flight_status"}
    if len(rows) != 5 or {row["metric"] for row in rows} != expected:
        raise ReadError("AUDIT_INCOMPLETE", status=409)
    if any(row["severity"] not in (0, 1, 2) for row in rows):
        raise ReadError("AUDIT_INVALID_SEVERITY", status=409)
    maximum = max(row["severity"] for row in rows)
    # Prefer a numeric cause when it ties with another metric.
    cause = sorted(
        rows,
        key=lambda r: (r["severity"], r["metric"] == "pax_count", r["value_num"] is not None),
        reverse=True,
    )[0]
    if cause["value_num"] is not None and maximum > 0:
        boundary = cause["crit"] if maximum == 2 else cause["warn"]
        unit = "passengers" if cause["metric"] == "pax_count" else cause["metric"]
        return (
            f"{cause['value_num']:g} {unit} ≥ "
            f"{'critical' if maximum == 2 else 'warning'} threshold {boundary:g}"
        )
    if maximum == 0:
        return "All five gate signals are within their governed healthy rules."
    return f"{cause['metric']}: {cause['value_str']} → {cause['status']}"


def gate_provenance(data, push_id: str, asset_id: str) -> dict:
    if asset_id not in {f"GATE_A{i}" for i in range(1, 9)}:
        raise ReadError("ASSET_NOT_FOUND", status=404)
    publication = data.publication(push_id)
    manifest = publication["manifest"]
    frozen = manifest.get("rules")
    status = "verified" if frozen else "legacy_rule_identity_unrecorded"
    rows = [row for row in manifest["metric_states"] if row["asset_id"] == asset_id]
    if len(rows) != 5:
        raise ReadError("AUDIT_INCOMPLETE", status=409)
    stamp = rows[0]["ts"]
    start = stamp if isinstance(stamp, datetime) else datetime.fromisoformat(stamp)
    parameters = {
        "run_id": manifest["run_id"],
        "asset_id": asset_id,
        "versions": manifest["delta_versions"],
        "thresholds": manifest["thresholds"],
        "start_ts": start.isoformat(),
        "end_ts": (start + timedelta(minutes=1)).isoformat(),
    }
    try:
        if frozen and frozen["rule_id"] != rule_snapshot()["rule_id"]:
            raise ReadError("AUDIT_RULE_UNAVAILABLE", status=410)
        scored = data.sql.read("asset_provenance", parameters)
        keys = ("metric", "value_num", "value_str", "warn", "crit", "severity", "status", "colour")

        def identity(values):
            return sorted(tuple(row[key] for key in keys) for row in values)

        if identity(scored) != identity(rows):
            raise ReadError("AUDIT_STATE_MISMATCH", status=409)
        if any(r["run_id"] != manifest["run_id"] or r["asset_id"] != asset_id for r in scored):
            raise ReadError("AUDIT_STATE_MISMATCH", status=409)
        rows = scored
    except ReadError as error:
        if error.status != 410:
            raise
        status = error.code
    explanation = explain(rows)
    gate = next(r for r in manifest["states"] if r["asset_id"] == asset_id)
    worst = max(rows, key=lambda r: r["severity"])
    if (gate["status"], gate["colour"]) != (worst["status"], worst["colour"]):
        raise ReadError("AUDIT_STATE_MISMATCH", status=409)
    return {
        "asset_id": asset_id,
        "explanation": explanation,
        "sensors": rows,
        "verification": status,
        "run_id": manifest["run_id"],
        "scenario": manifest["scenario"],
        "step": manifest["step"],
        "push_id": push_id,
        "delta_versions": manifest["delta_versions"],
        "rule": "Metric SQL severity → worst gate severity → governed hex colour",
        "rule_mode": frozen["replay_mode"]
        if frozen
        else "legacy canonical SQL; original rule identity not recorded",
        "run_url": run_url(data.config, manifest["run_id"]),
        "details": {
            "rules": frozen,
            "publisher": manifest.get("publisher"),
            "base_sha256": manifest["base_sha256"],
            "glb_sha256": manifest["glb_sha256"],
            "glb_path": manifest["glb_path"],
            "usd_path": manifest["usd_path"],
            "state_sha256": manifest["state_sha256"],
        },
    }
