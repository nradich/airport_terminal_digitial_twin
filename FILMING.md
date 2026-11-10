# Filming the airport twin

## Verified story

The same seed and flight schedule produce a quiet A4 after departure in baseline,
and 213 people with a critical red A4 when its flight is delayed. The baseline
peak is 126; the delayed peak is 213. Both runs have sixty metric steps.

| Scenario | Verified run ID |
| --- | --- |
| baseline | fec2d8ef61b94c4590b2ac3f624aae22 |
| delay_A4 | 8c9da58a294f4cbab4255799f79b34ec |

## Record the workflow

1. Open http://localhost:3000. Browse dbx_twin → airport. Show the five Delta
   tables, latest_state/gate_health views and scenes Volume. In sensor_readings,
   Sample data shows numeric value_num beside categorical value_str and run_id.
2. Explain that thresholds are governed Delta data. The local UC Spark catalog
   cannot execute stored SQL functions yet, so latest_state owns the colour/status
   expression. Open its Definition to inspect the SQL; do not claim UC function
   execution on this desktop.
3. In Notebooks, open the source files. Choose Python 3.11 (Airport UC Spark).
   The canonical source imports library functions; no business logic is copied
   into notebook cells. Browser execution and source saving were verified.
4. Run the complete pipeline from PowerShell in the adjacent LocalUnityCatalog
   checkout. These commands were executed successfully:

   ```powershell
   docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin run --scenario baseline --seed 42
   docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin run --scenario delay_A4 --seed 42
   ```

5. Copy the explicit run IDs from PIPELINE_OK. Never choose an implicit latest
   run. For separate interactive notebooks, add a parameter cell before the
   notebook's existing code, setting twin_params with scenario, seed, minutes,
   run_id and phase. Use phase="all" for full validation. Set run_id explicitly
   in 03 and 04; it is not shared automatically across independent kernels.
6. In Workspace Experiments select /Shared/airport-twin. Check the two scenario
   rows. The metric selector offers peak_pax_A4, gates_in_crit, avg_co2 and
   security_queue_p95, all plotted by simulation minute. The comparison survives
   opening a run's details.
7. In the delayed run's artifacts expand scene → runs → run ID → push ID and
   choose View PNG. Point to red A4 and amber security. Show manifest.json,
   thresholds.json and the USD state layer beside the image.
8. Native MLflow is http://localhost:5000/mlflow/. Choose Model training, compare
   the runs and select peak_pax_A4 for its native step chart. This was verified.
9. To open the scene in an OpenUSD viewer, retain the entire scenes Volume folder
   or download the run's scene artifact directory. The state layer composes with
   terminal_base.usda via relative paths. An actual Omniverse Kit viewer session
   remains UNTESTED; Kit streaming and GPU rendering are deferred to M5.

## Repeat without erasing history

Re-running either scenario creates another MLflow run and run-scoped Delta rows.
Pushes of unchanged state reuse the same publication ID. Setup preserves threshold
edits. Do not reset Docker volumes, truncate tables, or delete previous runs to
prepare a take. Restore deliberately edited thresholds to the captured values
before comparing new takes with earlier runs.

The preview retains a 16-active-file / 16-MiB input cap. Repeated small runs can
reach the file cap even when their total size is small. Between takes, compact
the affected tables in the platform-provided Spark notebook session:

```python
spark.sql("OPTIMIZE dbx_twin.airport.flights").collect()
spark.sql("OPTIMIZE dbx_twin.airport.sensor_readings").collect()
```

These statements were executed locally: each table went from 20 active files to
one. Bidirectional row comparisons with the previous Delta versions passed, and
the readings preview again returned 50 rows with all six typed columns. This
maintenance preserved all run rows and existing versions; no VACUUM was run.
Use your configured catalog/schema when changing the defaults. See
[Delta compaction documentation](https://docs.delta.io/optimizations-oss/).

Python source notebooks preserve code/Markdown cell boundaries, including empty
cells. Source files do not persist execution outputs or arbitrary .ipynb metadata;
ordinary .ipynb notebooks retain the existing Jupyter behavior.

The overlay points Workspace Notebooks at the airport service on 8889. The
original RAPIDS notebook service remains unchanged at
http://localhost:8888/jupyter/. The base platform configuration continues to
target it when the airport overlay is not applied.
