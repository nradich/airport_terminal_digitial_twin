"""Render standalone Databricks SQL for notebooks, the SQL editor, or MCP."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from airport_twin.config import Config
from airport_twin.data import ASSETS, THRESHOLDS, render, sql_text


def seed_sql(
    config: Config, table: str, rows: list[tuple], columns: list[str], keys: list[str]
) -> str:
    def literal(value: object) -> str:
        return "'" + value.replace("'", "''") + "'" if isinstance(value, str) else str(value)

    values = ",\n".join("(" + ",".join(literal(v) for v in row) + ")" for row in rows)
    condition = " AND ".join(f"t.{k}=s.{k}" for k in keys)
    return (
        f"MERGE INTO {config.table(table)} t USING (VALUES {values}) "
        f"AS s({','.join(columns)}) ON {condition} WHEN NOT MATCHED THEN INSERT *;"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="dbx_twin")
    parser.add_argument("--schema", default="airport")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--colour-logic", choices=["uc_function", "view_sql"], default="uc_function"
    )
    args = parser.parse_args()
    config = Config(catalog=args.catalog, schema=args.schema)
    values = {"namespace": config.namespace}
    for table in ("assets", "flights", "sensor_readings", "thresholds", "scene_pushes"):
        values[table + "_location"] = ""
    statements = [
        f"CREATE CATALOG IF NOT EXISTS {config.catalog};",
        f"CREATE SCHEMA IF NOT EXISTS {config.namespace};",
        render(sql_text("tables.sql"), values) + ";",
        f"CREATE VOLUME IF NOT EXISTS {config.namespace}.scenes;",
        seed_sql(
            config,
            "assets",
            ASSETS,
            ["asset_id", "asset_type", "zone", "prim_path", "display_name"],
            ["asset_id"],
        ),
        seed_sql(
            config,
            "thresholds",
            THRESHOLDS,
            ["asset_type", "metric", "warn", "crit"],
            ["asset_type", "metric"],
        ),
    ]
    colour = sql_text("colour.sql")
    if args.colour_logic == "uc_function":
        statements.append(render(sql_text("status_colour.sql"), values) + ";")
        colour = f"{config.namespace}.status_colour(severity, 1D, 2D)"
    values["colour_expression"] = colour
    for view in ("latest_state", "gate_health"):
        query = render(sql_text(view + ".sql"), values)
        statements.append(f"CREATE OR REPLACE VIEW {config.table(view)} AS {query};")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n\n".join(statements) + "\n", encoding="utf-8")
    logging.basicConfig(level=logging.INFO)
    logging.info("SQL_RENDER_OK path=%s (remote execution UNTESTED)", args.output)


if __name__ == "__main__":
    main()
