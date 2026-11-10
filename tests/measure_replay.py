"""Executed inside the read-only local App container; emits no credentials."""

import argparse
import json
import time
from datetime import datetime, timedelta

import requests

from airport_twin.readers import LocalSqlReader, ReadError

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run-id")
args = parser.parse_args()
if args.run_id:
    RUN = args.run_id
else:
    available = requests.get("http://localhost:8000/api/runs", timeout=45).json()
    candidates = [row["run_id"] for row in available if row["minutes"] == 120]
    if len(candidates) != 1:
        raise ValueError("Supply --run-id for an unambiguous 120-step fixture")
    RUN = candidates[0]
URL = f"http://localhost:8000/api/runs/{RUN}"
started = time.monotonic()
replays = requests.get(URL + "/replays", timeout=90)
replays.raise_for_status()
replay = replays.json()[0]
pages = []
for start in (0, 60):
    response = requests.get(
        URL + "/timeline",
        params={"replay_id": replay["replay_id"], "start_step": start, "end_step": start + 60},
        timeout=90,
    )
    response.raise_for_status()
    page = response.json()
    pages.append(page)
    print(
        json.dumps(
            {
                "range": [page["start_step"], page["end_step"]],
                "sql_rows": page["sql_rows"],
                "metric_points": page["metric_points"],
                "serialized_bytes": len(response.content),
            }
        ),
        flush=True,
    )
assert [f["step"] for p in pages for f in p["frames"]] == list(range(120))
params = {
    "run_id": RUN,
    "versions": replay["identity"]["delta_versions"],
    "thresholds": replay["identity"]["thresholds"],
    "start_ts": replay["start_ts"],
    "end_ts": (datetime.fromisoformat(replay["start_ts"]) + timedelta(minutes=120)).isoformat(),
}
reader = LocalSqlReader()
assert reader.read("raw_count", params) == [{"readings": 5040, "steps": 120}]
try:
    reader.read("raw_history", params)
except ReadError as error:
    assert error.code == "READ_LIMIT_EXCEEDED"
    print("RAW_120_STEP_LIMIT_CONFIRMED", flush=True)
else:
    raise AssertionError("Raw results must exceed 5000 rows")
missing = {**params, "versions": {**params["versions"], "sensor_readings": 99999999}}
try:
    reader.read("history", missing)
except ReadError as error:
    assert (error.code, error.status) == ("AUDIT_VERSION_UNAVAILABLE", 410), str(error)
    print("GENUINE_NONEXISTENT_VERSION_410_CONFIRMED", flush=True)
else:
    raise AssertionError("Missing history was silently substituted")
print(f"REPLAY_MEASURE_OK seconds={time.monotonic() - started:.3f}", flush=True)
