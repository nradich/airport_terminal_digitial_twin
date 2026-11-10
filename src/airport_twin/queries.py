"""Named read queries shared by the local gateway and Databricks SQL adapter."""

from __future__ import annotations

import re
from dataclasses import dataclass

from airport_twin.config import Config


@dataclass(frozen=True)
class ReadQuery:
    sql: str
    parameters: dict


def build_query(name: str, parameters: dict, config: Config) -> ReadQuery:
    """Allow only registered reads; never accept SQL, object names or paths."""
    c = config.namespace
    plain = {
        "assets": f"SELECT * FROM {c}.assets ORDER BY asset_id",
        "thresholds": f"SELECT * FROM {c}.thresholds ORDER BY asset_type,metric",
        "pushes": f"SELECT * FROM {c}.scene_pushes WHERE glb_path IS NOT NULL ORDER BY ts DESC",
    }
    from airport_twin.data import sql_text

    plain["palette"] = (
        "SELECT CASE severity WHEN 0 THEN 'ok' WHEN 1 THEN 'warn' ELSE 'crit' END status, "
        + sql_text("colour.sql")
        + " colour FROM VALUES (0),(1),(2) AS scores(severity)"
    )
    if name in plain:
        if parameters:
            raise ValueError("This query takes no parameters")
        return ReadQuery(plain[name], {})
    if name != "current" or set(parameters) != {"run_id"}:
        raise ValueError("Unknown named read or parameters")
    if not re.fullmatch(r"[a-f0-9]{32}", parameters["run_id"]):
        raise ValueError("Invalid run ID")
    return ReadQuery(
        f"SELECT asset_id,run_id,prim_path,status,colour,severity "
        f"FROM {c}.gate_health WHERE run_id=:run_id UNION ALL "
        f"SELECT asset_id,run_id,prim_path,status,colour,severity FROM {c}.latest_state "
        "WHERE run_id=:run_id AND asset_type <> 'gate'",
        parameters,
    )
