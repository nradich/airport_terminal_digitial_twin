# Airport terminal digital twin

An OpenUSD airport concourse driven by Unity Catalog, Delta, and MLflow. Eight
gates and two shared zones; deterministic baseline and `delay_A4` scenarios.

## Current status

Live platform discovery and M0 contracts passed. M1 setup, seeded simulation,
and data validation ran against real UC/Delta/MLflow. Scene authoring is next.
No remote deployment has been attempted.

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
