"""Disposable parity checks using platform compute and isolated UC objects."""

from __future__ import annotations

import hashlib
import logging
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from airport_twin.data import render, sql_text
from airport_twin.platform import Platform
from airport_twin.tracking import client

LOG = logging.getLogger(__name__)


def run_contracts(platform: Platform) -> dict:
    """Never reset a twin object. Cleanup is confined to a unique scratch schema."""
    schema = "airport_contract_" + uuid4().hex[:12]
    config = replace(platform.config, schema=schema)
    scratch = Platform(config, platform.spark)
    table, view = config.table("assets"), config.table("latest_state")
    created_function = False
    run_id = None
    tracking = client(config)
    result = {"schema": config.namespace, "platform": config.platform}
    try:
        scratch.setup_namespace()
        platform.spark.sql(
            f"CREATE TABLE {table} (id BIGINT) USING DELTA" + scratch.table_location("assets")
        )
        platform.spark.sql(f"INSERT INTO {table} VALUES (42)")
        scratch.ensure_view("latest_state", f"SELECT id FROM {table} WHERE id=42")
        fresh = platform.spark.newSession()
        assert fresh.sql(f"SELECT id FROM {table}").first()[0] == 42
        assert fresh.sql(f"SELECT id FROM {view}").first()[0] == 42
        folder = scratch.setup_volume()
        payload = b"airport parity contract\n"
        (folder / "proof.bin").write_bytes(payload)
        assert (scratch.volume_root() / "proof.bin").read_bytes() == payload
        function_sql = render(sql_text("status_colour.sql"), {"namespace": config.namespace})
        try:
            platform.spark.sql(function_sql)
            created_function = True
        except Exception as error:
            if config.platform != "local" or "not support" not in str(error).lower():
                raise
        colour = (
            f"{config.namespace}.status_colour(value,120D,180D)"
            if created_function
            else sql_text("status_colour.sql")
            .split("RETURN ", 1)[1]
            .replace("warn", "120D")
            .replace("crit", "180D")
        )
        edges = platform.spark.sql(
            "SELECT " + colour + " colour FROM VALUES "
            "(0D),(119.999D),(120D),(180D),(CAST(NULL AS DOUBLE)) AS edges(value)"
        ).collect()
        assert [r[0] for r in edges] == ["#22C55E", "#22C55E", "#F59E0B", "#EF4444", None]
        experiment = tracking.get_experiment_by_name("/Shared/airport-twin-contracts")
        exp_id = (
            experiment.experiment_id
            if experiment
            else tracking.create_experiment("/Shared/airport-twin-contracts")
        )
        run_id = tracking.create_run(exp_id, tags={"contract_schema": config.namespace}).info.run_id
        tracking.log_artifact(run_id, str(folder / "proof.bin"))
        with tempfile.TemporaryDirectory() as destination:
            artifact = tracking.download_artifacts(run_id, "proof.bin", destination)
            assert Path(artifact).read_bytes() == payload
        result.update(
            persistent_table=True,
            persistent_view=True,
            volume_roundtrip=True,
            mlflow_roundtrip=True,
            artifact_sha256=hashlib.sha256(payload).hexdigest(),
            colour_mode="uc_function" if created_function else "view_sql",
        )
    finally:
        if run_id:
            tracking.set_terminated(run_id)
            tracking.delete_run(run_id)
        assert config.schema == schema and schema.startswith("airport_contract_")
        if created_function:
            platform.spark.sql(f"DROP FUNCTION {config.namespace}.status_colour")
        platform.spark.sql(f"DROP VIEW IF EXISTS {view}")
        platform.spark.sql(f"DROP TABLE IF EXISTS {table}")
        if config.platform == "local":
            from platform_runtime import catalog_request
            from requests import HTTPError

            for path in (f"/volumes/{config.namespace}.scenes", f"/schemas/{config.namespace}"):
                try:
                    catalog_request("DELETE", path)
                except HTTPError as error:
                    if error.response.status_code != 404:
                        raise
            for base in (Path("/data/twin/tables"), Path("/data/twin/volumes")):
                target = (base / config.catalog / schema).resolve()
                assert target.parent == (base / config.catalog).resolve() and target.name == schema
                if target.exists():
                    shutil.rmtree(target)
        else:
            platform.spark.sql(f"DROP VOLUME IF EXISTS {config.namespace}.scenes")
            platform.spark.sql(f"DROP SCHEMA {config.namespace}")
    LOG.info("CONTRACTS_OK %s", result)
    return result
