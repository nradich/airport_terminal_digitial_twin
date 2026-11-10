# Local retest — 2026-11-09

Verified the clone at
`C:\Users\nicho\Desktop\Workspace\Databricks\airport_term_digital_twin`.
Origin is https://github.com/nradich/airport_terminal_digitial_twin.git, branch
`codex/airport-twin`. Tested source commit:
`5603be465403a4d714b416ffd1f9fdc2f2d8530e`. The working tree was clean before
testing. No remote push or deployment was performed.

## Results

- All eight local services healthy; existing RAPIDS service preserved.
- Live UC/Delta/view/Volume/MLflow contract: **1 passed in 12.66s**.
- Full airport suite, including live SQL and tracking: **23 passed in 24.74s**.
- Ruff: **All checks passed!**
- Both scenarios completed source notebooks 00 → 01 → 02 → 03 → 04. Each
  validated ten assets, eight flights, 2,520 readings, 42 latest metric states,
  eight gate-health rows and retrieved USD/PNG/provenance artifacts.

| Scenario | MLflow run ID | Peak A4 | Final A4 | Simulation/write time |
| --- | --- | --- | --- | --- |
| baseline | 5767b836d78146fdab7d786a1795f8c7 | 126 | ok / #22C55E | 2.221s |
| delay_A4 | 7a617dc8b34b41f98b02725e04db4944 | 213 | crit / #EF4444 | 3.920s |

Read back the live tracking records: both runs are FINISHED, have the tested Git
SHA, identical seed/minutes/start/threshold parameters, and all four metric
histories contain steps 0..59. Downloaded each publication manifest and heatmap.

## Preview maintenance discovered during testing

The Workspace readings preview initially rejected 20 active files, exceeding
its intentional 16-file cap. Delta OPTIMIZE compacted readings and flights to
one active file each. Bidirectional exceptAll comparisons proved current rows
equal the retained previous-version rows. Readings retained 25,200 rows and
flights retained 80 rows across ten runs. No VACUUM or deletion was performed.
The Workspace readings preview then returned 50 rows and all six typed columns.
FILMING.md includes the tested maintenance statements.

## Reproduce

From the adjacent LocalUnityCatalog checkout in PowerShell (all executed):

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks python -m pytest -q -o cache_dir=/tmp/platform-pytest /opt/platform/test_contracts.py
docker compose -f compose.yaml -f compose.spark.yaml exec -T -e TWIN_RUN_INTEGRATION=1 spark-notebooks uv run --no-sync pytest -q
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync ruff check src tests notebooks scripts
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin run --scenario baseline --seed 42
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin run --scenario delay_A4 --seed 42
```

Workspace: http://localhost:3000. Native MLflow:
http://localhost:5000/mlflow/#/experiments/5. Select the explicit run IDs above.

Remaining limitations: local UC function support uses the documented governed
view fallback; preview input limits remain enforced. Real Databricks validation
and execution, and opening the scene in Omniverse Kit, remain UNTESTED. See
PORTABILITY.md for the incomplete M4 proof.
