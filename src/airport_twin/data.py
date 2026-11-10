"""Seed data and portable SQL setup."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from airport_twin.platform import Platform

LOG = logging.getLogger(__name__)
ASSETS = [
    (f"GATE_A{i}", "gate", "Concourse_A", f"/World/Concourse_A/Gate_A{i}", f"Gate A{i}")
    for i in range(1, 9)
] + [
    ("SECURITY", "security", "Security", "/World/Security", "Security checkpoint"),
    ("BAGGAGE", "baggage", "Baggage", "/World/Baggage", "Baggage claim"),
]
THRESHOLDS = [
    ("gate", "pax_count", 120.0, 180.0),
    ("gate", "hvac_temp_c", 26.0, 29.0),
    ("gate", "co2_ppm", 1000.0, 1500.0),
    ("security", "queue_len", 40.0, 80.0),
    ("baggage", "belt_load_pct", 75.0, 95.0),
]
READING_SCHEMA = (
    "asset_id STRING, ts TIMESTAMP, metric STRING, "
    "value_num DOUBLE, value_str STRING, run_id STRING"
)
ASSET_NAMES = {f"GATE_A{i}": f"A{i}" for i in range(1, 9)} | {
    "SECURITY": "Security",
    "BAGGAGE": "Baggage",
}
FLIGHT_SCHEMA = (
    "flight_id STRING, gate_id STRING, sched_dep TIMESTAMP, "
    "actual_dep TIMESTAMP, status STRING, run_id STRING"
)


def sql_text(name: str) -> str:
    folder = Path(__file__).parent / "sql"
    if not folder.exists():
        folder = Path(__file__).parents[1] / "sql"
    return (folder / name).read_text(encoding="utf-8").strip().rstrip(";")


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text:
        raise ValueError("Unresolved SQL template")
    return text


def merge_rows(
    platform: Platform,
    table: str,
    rows: list[tuple],
    schema: str,
    keys: list[str],
    update: bool = False,
) -> None:
    """MERGE by logical key; retries cannot append duplicate readings or pushes."""
    from uuid import uuid4

    if not rows:
        return
    name = "twin_input_" + uuid4().hex
    platform.spark.createDataFrame(rows, schema).createOrReplaceTempView(name)
    condition = " AND ".join(f"t.{k} = s.{k}" for k in keys)
    matched = "WHEN MATCHED THEN UPDATE SET *" if update else ""
    try:
        platform.spark.sql(
            f"MERGE INTO {platform.config.table(table)} t USING {name} s "
            f"ON {condition} {matched} WHEN NOT MATCHED THEN INSERT *"
        )
    finally:
        platform.spark.catalog.dropTempView(name)


def setup(platform: Platform) -> dict[str, Any]:
    platform.setup_namespace()
    values = {"namespace": platform.config.namespace}
    for table in ("assets", "flights", "sensor_readings", "thresholds", "scene_pushes"):
        values[table + "_location"] = platform.table_location(table)
    for statement in render(sql_text("tables.sql"), values).split(";"):
        if statement.strip():
            platform.spark.sql(statement)
    if "asset_name" not in platform.spark.table(platform.config.table("assets")).columns:
        platform.spark.sql(
            f"ALTER TABLE {platform.config.table('assets')} ADD COLUMNS (asset_name STRING)"
        )
    push_columns = platform.spark.table(platform.config.table("scene_pushes")).columns
    missing = [
        f"{name} {kind}"
        for name, kind in (
            ("scenario", "STRING"),
            ("step", "INT"),
            ("preview_path", "STRING"),
            ("capture_path", "STRING"),
            ("glb_path", "STRING"),
            ("glb_sha256", "STRING"),
        )
        if name not in push_columns
    ]
    if missing:
        platform.spark.sql(
            f"ALTER TABLE {platform.config.table('scene_pushes')} "
            f"ADD COLUMNS ({', '.join(missing)})"
        )
    for name in ("assets", "flights", "sensor_readings", "thresholds", "scene_pushes"):
        properties = {
            r.key: r.value
            for r in platform.spark.sql(
                f"SHOW TBLPROPERTIES {platform.config.table(name)}"
            ).collect()
        }
        retention = {
            key: "interval 365 days"
            for key in ("delta.deletedFileRetentionDuration", "delta.logRetentionDuration")
        }
        if any(properties.get(key) != value for key, value in retention.items()):
            assignments = ", ".join(f"'{key}'='{value}'" for key, value in retention.items())
            platform.spark.sql(
                f"ALTER TABLE {platform.config.table(name)} SET TBLPROPERTIES ({assignments})"
            )
    merge_rows(
        platform,
        "assets",
        [(*row, ASSET_NAMES[row[0]]) for row in ASSETS],
        "asset_id STRING, asset_type STRING, zone STRING, prim_path STRING, "
        "display_name STRING, asset_name STRING",
        ["asset_id"],
    )
    names = " ".join(f"WHEN '{key}' THEN '{value}'" for key, value in ASSET_NAMES.items())
    platform.spark.sql(
        f"UPDATE {platform.config.table('assets')} SET asset_name = CASE asset_id {names} END "
        "WHERE asset_name IS NULL"
    )
    actual = {
        tuple(r)
        for r in platform.spark.table(platform.config.table("assets"))
        .select("asset_id", "asset_type", "zone", "prim_path", "display_name")
        .collect()
    }
    if actual != set(ASSETS):
        raise ValueError("Existing assets differ from the v1 layout; explicit migration required")
    merge_rows(
        platform,
        "thresholds",
        THRESHOLDS,
        "asset_type STRING, metric STRING, warn DOUBLE, crit DOUBLE",
        ["asset_type", "metric"],
    )
    platform.setup_volume()
    colour = sql_text("colour.sql")
    mode = "view_sql"
    # A bounded native attempt. Do not implement a custom JVM function evaluator here.
    try:
        platform.spark.sql(
            render(sql_text("status_colour.sql"), {"namespace": platform.config.namespace})
        )
    except Exception as exc:
        message = str(exc)
        if not any(
            term in message.lower() for term in ("unsupported", "not support", "parse_syntax_error")
        ):
            raise
        LOG.warning(
            "UC SQL function unavailable; governed latest_state SQL active: %s",
            message.splitlines()[0],
        )
    else:
        result = platform.spark.sql(
            f"SELECT {platform.config.namespace}.status_colour(2D,1D,2D)"
        ).first()[0]
        if result != "#EF4444":
            raise AssertionError("Qualified colour function failed boundary check")
        mode = "uc_function"
        colour = f"{platform.config.namespace}.status_colour(severity, 1D, 2D)"
    values = {
        "namespace": platform.config.namespace,
        "colour_expression": colour,
        "time_partition": "",
        "time_column": "",
        "readings": platform.config.table("sensor_readings"),
        "state_source": platform.config.table("latest_state"),
    }
    for view in ("latest_state", "gate_health"):
        platform.ensure_view(view, render(sql_text(view + ".sql"), values))
    LOG.info("SETUP_OK namespace=%s colour_logic=%s", platform.config.namespace, mode)
    return {"colour_logic": mode}
