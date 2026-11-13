"""Named read queries shared by the local gateway and Databricks SQL adapter."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime

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
    if name in {"history", "raw_history", "raw_count", "asset_provenance", "busiest"}:
        return history_query(name, parameters, config)
    if name == "journeys" and set(parameters) == {"push_id"}:
        if not re.fullmatch(r"[0-9a-f]{64}", parameters["push_id"]):
            raise ValueError("Invalid journey publication")
        return ReadQuery(
            f"SELECT run_id, source_run, input_json, summary_json FROM {c}.journey_experiments "
            "WHERE push_id=:push_id ORDER BY flight_id, run_id LIMIT 32", parameters,
        )
    if name == "journey_durations" and set(parameters) == {
        "run_id", "checkpoint", "bag", "coffee", "restroom"
    }:
        if (not re.fullmatch(r"[0-9a-f]{32}", parameters["run_id"])
                or parameters["checkpoint"] not in {"standard", "precheck"}
                or any(type(parameters[k]) is not int or parameters[k] not in (0, 1)
                       for k in ("bag", "coffee", "restroom"))):
            raise ValueError("Invalid journey profile")
        return ReadQuery(
            "SELECT lanes, to_json(array_sort(collect_list("
            "named_struct('seconds', seconds, 'n', n)))) "
            f"AS histogram FROM (SELECT lanes, seconds, count(*) AS n FROM (SELECT lanes, "
            f"security_wait + screening + walk + :bag * bag + :coffee * coffee + "
            f":restroom * restroom AS seconds FROM {c}.journey_trials WHERE run_id=:run_id "
            f"AND checkpoint=:checkpoint) GROUP BY lanes, seconds) GROUP BY lanes ORDER BY lanes",
            parameters,
        )
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


def history_query(name: str, parameters: dict, config: Config) -> ReadQuery:
    """Score version-pinned readings with the exact published threshold snapshot."""
    from airport_twin.data import render, sql_text

    expected = {"run_id", "versions", "thresholds", "start_ts", "end_ts"}
    if name == "asset_provenance":
        expected.add("asset_id")
        if parameters.get("asset_id") not in {f"GATE_A{i}" for i in range(1, 9)}:
            raise ValueError("Unknown gate")
    if set(parameters) != expected or not re.fullmatch(r"[a-f0-9]{32}", parameters["run_id"]):
        raise ValueError("Invalid historical read parameters")
    versions = parameters["versions"]
    if set(versions) != {"assets", "flights", "sensor_readings", "thresholds"} or any(
        type(v) is not int or not 0 <= v < 2**63 for v in versions.values()
    ):
        raise ValueError("Invalid source versions")
    start, end = (datetime.fromisoformat(parameters[k]) for k in ("start_ts", "end_ts"))
    if start.tzinfo or end.tzinfo or not 0 < (end - start).total_seconds() <= 240 * 60:
        raise ValueError("Historical range must be 1..240 UTC simulation minutes")
    c = config.namespace
    source = (
        f"SELECT * FROM {c}.sensor_readings VERSION AS OF {versions['sensor_readings']} "
        "WHERE run_id=:run_id AND ts>=CAST(:start_ts AS TIMESTAMP) "
        "AND ts<CAST(:end_ts AS TIMESTAMP)"
    )
    args = {key: parameters[key] for key in ("run_id", "start_ts", "end_ts")}
    if name in {"raw_history", "raw_count"}:
        return ReadQuery(
            source
            if name == "raw_history"
            else f"SELECT count(*) readings,count(DISTINCT ts) steps FROM ({source})",
            args,
        )
    limits = parameters["thresholds"]
    allowed = {
        ("gate", "pax_count"),
        ("gate", "hvac_temp_c"),
        ("gate", "co2_ppm"),
        ("security", "queue_len"),
        ("baggage", "belt_load_pct"),
    }
    if len(limits) != 5 or {(r[0], r[1]) for r in limits} != allowed:
        raise ValueError("Incomplete threshold snapshot")
    values = []
    for i, (asset_type, metric, warn, crit) in enumerate(sorted(limits)):
        if (
            not all(type(v) in (int, float) and math.isfinite(v) for v in (warn, crit))
            or warn >= crit
        ):
            raise ValueError("Invalid published thresholds")
        args.update(
            {f"asset_{i}": asset_type, f"metric_{i}": metric, f"warn_{i}": warn, f"crit_{i}": crit}
        )
        values.append(
            f"(:asset_{i},:metric_{i},CAST(:warn_{i} AS DOUBLE),CAST(:crit_{i} AS DOUBLE))"
        )
    threshold_source = (
        "(SELECT * FROM VALUES " + ",".join(values) + " AS limits(asset_type,metric,warn,crit))"
    )
    settings = {
        "namespace": c,
        "readings": "(" + source + ")",
        "time_partition": ", ts",
        "time_column": ", ts",
        "state_source": "metrics",
        "assets_source": f"{c}.assets VERSION AS OF {versions['assets']}",
        "thresholds_source": threshold_source,
        "colour_expression": sql_text("colour.sql"),
    }
    metrics = render(sql_text("latest_state.sql"), settings)
    if name == "asset_provenance":
        args["asset_id"] = parameters["asset_id"]
        return ReadQuery(
            f"SELECT * FROM ({metrics}) WHERE asset_id=:asset_id ORDER BY metric", args
        )
    gates = render(sql_text("gate_health.sql"), settings)
    if name == "busiest":
        # Worst status first, then combined severity, queue length, gate crowd and earliest tie.
        return ReadQuery(
            f"WITH metrics AS ({metrics}), gates AS ({gates}) "
            "SELECT s.ts FROM metrics s JOIN gates g ON s.ts=g.ts "
            "JOIN metrics pax ON pax.ts=g.ts AND pax.asset_id=g.asset_id AND pax.metric='pax_count' "
            "WHERE s.asset_id='SECURITY' AND s.metric='queue_len' AND g.asset_id='GATE_A4' "
            "ORDER BY greatest(s.severity,g.severity) DESC, (s.severity+g.severity) DESC, "
            "s.value_num DESC, pax.value_num DESC, s.ts LIMIT 1", args,
        )
    sql = (
        f"WITH metrics AS ({metrics}), gates AS ({gates}), states AS ("
        "SELECT asset_id,run_id,ts,prim_path,status,colour,severity FROM gates UNION ALL "
        "SELECT asset_id,run_id,ts,prim_path,status,colour,severity FROM metrics "
        "WHERE asset_type<>'gate'), "
        "measurements AS (SELECT asset_id,ts,"
        "max(CASE WHEN metric='pax_count' THEN value_num END) pax_count,"
        "max(CASE WHEN metric='hvac_temp_c' THEN value_num END) hvac_temp_c,"
        "max(CASE WHEN metric='co2_ppm' THEN value_num END) co2_ppm,"
        "max(CASE WHEN metric='flight_status' THEN value_str END) flight_status,"
        "max(CASE WHEN metric='jet_bridge_status' THEN value_str END) jet_bridge_status "
        "FROM metrics GROUP BY asset_id,ts) SELECT s.*,m.pax_count,m.hvac_temp_c,m.co2_ppm,"
        "m.flight_status,m.jet_bridge_status FROM states s JOIN measurements m "
        "ON s.asset_id=m.asset_id AND s.ts=m.ts ORDER BY s.ts,s.asset_id"
    )
    return ReadQuery(sql, args)
