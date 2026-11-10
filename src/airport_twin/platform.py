"""Thin platform differences. Compute always uses the platform's Spark session."""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from airport_twin.config import Config

LOG = logging.getLogger(__name__)


class Platform:
    def __init__(self, config: Config, spark: Any) -> None:
        self.config, self.spark = config, spark

    def setup_namespace(self) -> None:
        c = self.config
        if c.platform == "local":
            from platform_runtime import ensure_metadata

            ensure_metadata("/catalogs", c.catalog, {"name": c.catalog})
            ensure_metadata("/schemas", c.namespace, {"name": c.schema, "catalog_name": c.catalog})
        else:
            self.spark.sql(f"CREATE CATALOG IF NOT EXISTS {c.catalog}")
            self.spark.sql(f"CREATE SCHEMA IF NOT EXISTS {c.namespace}")

    def table_location(self, name: str) -> str:
        self.config.table(name)
        if self.config.platform == "local":
            path = f"file:///data/twin/tables/{self.config.catalog}/{self.config.schema}/{name}"
            return f" LOCATION '{path}'"
        return ""

    def setup_volume(self) -> Path:
        c = self.config
        if c.platform == "local":
            from platform_runtime import ensure_metadata

            ensure_metadata(
                "/volumes",
                c.namespace + ".scenes",
                {
                    "name": "scenes",
                    "catalog_name": c.catalog,
                    "schema_name": c.schema,
                    "volume_type": "EXTERNAL",
                    "storage_location": f"file:///data/twin/volumes/{c.catalog}/{c.schema}/scenes",
                },
            )
        else:
            self.spark.sql(f"CREATE VOLUME IF NOT EXISTS {c.namespace}.scenes")
        folder = self.volume_root()
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def volume_root(self) -> Path:
        c = self.config
        if c.platform == "local":
            from platform_runtime import volume_path

            return volume_path(c.namespace + ".scenes")
        return Path(f"/Volumes/{c.catalog}/{c.schema}/scenes")

    def ensure_view(self, name: str, query: str) -> None:
        full = self.config.table(name)
        if self.config.platform == "local":
            from platform_runtime import catalog_request
            from requests import HTTPError

            try:
                old = catalog_request("GET", "/tables/" + full)
            except HTTPError as exc:
                if exc.response.status_code != 404:
                    raise
            else:
                if old["table_type"] != "VIEW":
                    raise ValueError(f"Refusing to replace non-view {full}")
                if " ".join(old["view_definition"].split()) == " ".join(query.split()):
                    return
                # UC OSS 0.7 does not support replacing views. Documented setup-only gap.
                self.spark.sql(f"DROP VIEW {full}")
            self.spark.sql(f"CREATE VIEW {full} AS {query}")
        else:
            self.spark.sql(f"CREATE OR REPLACE VIEW {full} AS {query}")

    def versions(self) -> dict[str, int]:
        return {
            name: int(
                self.spark.sql(f"DESCRIBE HISTORY {self.config.table(name)} LIMIT 1").first()[
                    "version"
                ]
            )
            for name in ("assets", "flights", "sensor_readings", "thresholds")
        }


def notebook_context(namespace: dict[str, Any]) -> tuple[Config, Platform, dict[str, Any]]:
    """Use injected globals locally; real notebook widgets/task values remotely."""
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("airport_twin").setLevel(logging.INFO)
    config = Config.from_env()
    if config.platform == "databricks":
        utils = namespace["dbutils"]
        values = {}
        for name, default in {
            "TWIN_CATALOG": config.catalog,
            "TWIN_SCHEMA": config.schema,
            "TWIN_EXPERIMENT": config.experiment,
            "TWIN_PLATFORM": config.platform,
            "MLFLOW_TRACKING_URI": config.tracking_uri,
            "MLFLOW_REGISTRY_URI": config.registry_uri,
            "TWIN_GIT_SHA": os.getenv("TWIN_GIT_SHA", ""),
        }.items():
            utils.widgets.text(name, default)
            values[name] = utils.widgets.get(name)
        config = replace(
            config,
            catalog=values["TWIN_CATALOG"],
            schema=values["TWIN_SCHEMA"],
            experiment=values["TWIN_EXPERIMENT"],
            platform=values["TWIN_PLATFORM"],
            tracking_uri=values["MLFLOW_TRACKING_URI"],
            registry_uri=values["MLFLOW_REGISTRY_URI"],
        )
        if values["TWIN_GIT_SHA"]:
            os.environ["TWIN_GIT_SHA"] = values["TWIN_GIT_SHA"]
    if "spark" not in namespace:
        raise RuntimeError("The platform must supply spark; do not create an application engine")
    namespace["spark"].sql("SET TIME ZONE 'UTC'")
    params = namespace.get("twin_params")
    if params is None and config.platform == "local":
        params = {"scenario": "baseline", "seed": 42, "minutes": 60, "run_id": "", "phase": "all"}
        namespace["twin_params"] = params
    if params is None:
        utils = namespace["dbutils"]
        for key, default in (
            ("scenario", "baseline"),
            ("seed", "42"),
            ("minutes", "60"),
            ("run_id", ""),
            ("phase", "all"),
            ("run_ids", ""),
            ("step", "-1"),
            ("capture_dir", f"/Volumes/{config.catalog}/{config.schema}/scenes/capture_inbox"),
        ):
            utils.widgets.text(key, default)
        params = {
            key: utils.widgets.get(key)
            for key in (
                "scenario",
                "seed",
                "minutes",
                "run_id",
                "phase",
                "run_ids",
                "step",
                "capture_dir",
            )
        }
    if isinstance(params.get("run_ids"), str):
        params["run_ids"] = [
            value.strip() for value in params["run_ids"].split(",") if value.strip()
        ]
    return config, Platform(config, namespace["spark"]), params
