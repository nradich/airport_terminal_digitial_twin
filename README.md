# Airport terminal digital twin

An OpenUSD airport concourse driven by Unity Catalog, Delta, and MLflow. Eight
gates and two shared zones; deterministic baseline and `delay_A4` scenarios.

## Current status

Live platform discovery and M0 contracts passed. M1 setup, seeded simulation,
and data validation ran against real UC/Delta/MLflow. M2 also published and
validated a composed ten-asset USD scene without changing the base.
M3 verified both scenarios, complete MLflow metric histories and downloadable
USD/PNG/provenance artifacts, including native UI comparison.
No remote deployment has been attempted.

M4 packaging and offline schema checks pass. Authenticated bundle validation and
real Databricks execution are **UNTESTED** because no credentials are configured;
M4 remains incomplete. See [portability evidence](docs/PORTABILITY.md).

- [Verified local platform](docs/LOCAL_PLATFORM.md)
- [Parity and adapters](docs/PARITY.md)
- [Platform requests](docs/PLATFORM_ASKS.md)
- [Decisions](docs/DECISIONS.md)

The adjacent LocalUnityCatalog checkout owns the local compute environment. Its
existing Python 3.12 RAPIDS service remains separate and unchanged. Airport code
will run on Python 3.11 without GPU-specific imports. There is no side database.

## Run M1 locally

From the adjacent LocalUnityCatalog checkout in PowerShell (these commands were
executed here):

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin data --scenario baseline --seed 42
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync ruff check src tests notebooks
docker compose -f compose.yaml -f compose.spark.yaml exec -T -e TWIN_RUN_INTEGRATION=1 spark-notebooks uv run --no-sync pytest -q
```

First-time service/dependency setup is documented in the platform checkout's
docs/spark-platform.md. Install airport dependencies with `uv sync --inexact`
inside the service, using its system-site-packages virtual environment. Spark
is supplied by the platform, never installed by the airport package.

The source notebooks execute in order through the real Jupyter kernel. Logs
report the run ID explicitly; later push/validate commands require that ID.
M1 produces ten assets, eight flights, and 2,520 readings for sixty minutes.
The local SQL-function attempt is unsupported, so latest_state governs colour
and status directly. Seeded baseline simulation, Delta writes, and MLflow
metrics completed in 6.644 seconds on this desktop.

## Run the scene pipeline

Executed locally from the same platform checkout:

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin run --scenario baseline --seed 42
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin run --scenario delay_A4 --seed 42
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin push --run-id 9b5f798c2b114d9ea1622bb0e5b8d8f4
```

The first two commands execute 00 → 01 → 02 → 03 → 04 for each scenario. Copy
the explicit run ID for later pushes; the third command retries a verified run.
The scenes Volume contains terminal_base.usda and immutable publications under
runs/<run_id>/<push_id>/. Open the terminal_state_<run_id>.usda layer in an
OpenUSD viewer with its relative base path intact. Omniverse Kit streaming is
deferred; no RTX GPU is used by this pipeline.

Open [native MLflow](http://localhost:5000/mlflow/), choose **Model training**,
then `/Shared/airport-twin`. Compare baseline `fec2d8ef` with delay `8c9da58a` and
select peak_pax_A4 to see minute steps 0..59. The delayed run peaks at 213 people;
baseline peaks at 126. In each run, expand scene/runs/<run>/<push> for the PNG,
USD, thresholds and manifest. Full validation downloads these artifacts and
reopens the composed USD, rather than only listing metadata.

## Portable artifacts

Executed inside the same local service:

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv build --wheel
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks python scripts/prepare_offline.py
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync python scripts/render_sql.py --output .local/setup_databricks.sql
```

The wheel is in dist; the 90-file offline wheelhouse and checksums are in
.local/wheelhouse. The generated SQL targets Databricks managed tables and can
be pasted into its SQL editor after reviewing names and permissions. Its remote
execution is UNTESTED. Implementation commits are pushed on codex/airport-twin;
no Databricks upload or deployment was performed.
