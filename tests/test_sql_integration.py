"""Exercise the installed persistent view SQL against temporary edge-case inputs."""

import os
from datetime import datetime
from uuid import uuid4

import pytest

from airport_twin.config import Config
from airport_twin.data import READING_SCHEMA

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("TWIN_RUN_INTEGRATION") != "1", reason="requires live UC Spark"),
]


def test_governed_view_edges_and_typed_values():
    from platform_runtime import catalog_request, spark_session

    config = Config.from_env()
    spark = spark_session(config.catalog)
    query = catalog_request("GET", "/tables/" + config.table("latest_state"))["view_definition"]
    threshold = (
        spark.table(config.table("thresholds"))
        .where("asset_type = 'gate' AND metric = 'pax_count'")
        .first()
    )
    values = [threshold.warn - 0.01, threshold.warn, threshold.crit - 0.01, threshold.crit]
    expected = ["ok", "warn", "warn", "crit"]
    rows = [
        ("GATE_A1", datetime(2026, 1, 1), "pax_count", float(v), None, f"edge{i}")
        for i, v in enumerate(values)
    ]
    rows.extend(
        [
            ("GATE_A1", datetime(2026, 1, 1), "jet_bridge_status", None, "fault", "fault"),
            ("GATE_A1", datetime(2026, 1, 1), "flight_status", None, "delayed", "delay"),
            ("GATE_A1", datetime(2026, 1, 1), "pax_count", None, None, "missing"),
            ("GATE_A1", datetime(2026, 1, 1), "pax_count", float("nan"), None, "nan"),
        ]
    )
    name = "edge_input_" + uuid4().hex
    spark.createDataFrame(rows, READING_SCHEMA).createOrReplaceTempView(name)
    try:
        result = {
            r.run_id: r
            for r in spark.sql(query.replace(config.table("sensor_readings"), name)).collect()
        }
        assert [result[f"edge{i}"].status for i in range(4)] == expected
        assert result["fault"].colour == "#EF4444"
        assert result["delay"].status == "warn"
        assert result["missing"].status is None
        assert result["nan"].colour is None
    finally:
        spark.catalog.dropTempView(name)
        spark.stop()
