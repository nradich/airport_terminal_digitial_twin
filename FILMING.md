# Filming the airport twin

## Verified story

The same seed and flight schedule produce a quiet A4 after departure in baseline,
and 213 people with a critical red A4 when its flight is delayed. The baseline
peak is 126; the delayed peak is 213. Both runs have sixty metric steps.

| Scenario | Verified run ID |
| --- | --- |
| baseline | 5767b836d78146fdab7d786a1795f8c7 |
| delay_A4 | 7a617dc8b34b41f98b02725e04db4944 |

## 60-second take

Use the Airport snapshots panel with Film mode checked. Select Overview and
Baseline, then scrub to minute 59 before recording. The panel shows the exact
run, minute, scene push and four MLflow metrics. Gate names come from UC assets;
the legend shows current UC thresholds with inclusive warning/critical edges.

Direct scrubbing, Play/Pause, paused-frame capture and Open in MLflow were
exercised on 2026-11-10. Pausing during a blend settles the target minute's exact
colours and audit identity together. Click the scrubber track to jump to a minute;
Play resumes from it. The native MLflow peak_pax_A4 chart showed both complete
0–59 histories, with peaks 126 (baseline) and 213 (delay_A4).

| Time | Shot | Narration cue |
| --- | --- | --- |
| 0–10s | Overview, Baseline, minute 59 | Eight gates, two shared zones. A4 has departed; its final population is six. |
| 10–20s | Click Delay A4; hold through the 1.5s ripple | The delayed flight leaves 213 passengers at A4. The warning spreads to security. |
| 20–30s | Gate A4 close-up | Red is a governed critical state. Show run ID, push ID and threshold key. |
| 30–42s | Overview; Replay, Pause, scrub minutes 40–59 | This replays minute readings from the selected run, with matching MLflow metric steps. |
| 42–60s | Open in MLflow; compare the two explicit runs | Compare peak_pax_A4: 126 versus 213. Open the push's USD, viewport PNG and provenance. |

The travelling highlight is a presentation transition. Final colours, statuses
and displayed metrics always use the selected run and simulation minute. The
simple boxes/cylinders are an operational diagram, not a detailed terminal model.

## Prepare the film viewer

Run in the adjacent LocalUnityCatalog checkout. These use the same source
notebooks and platform-provided Python 3.11 Spark session as the main pipeline:

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin prepare-viewer --run-ids 5767b836d78146fdab7d786a1795f8c7 7a617dc8b34b41f98b02725e04db4944
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync python scripts/export_viewer.py --run-id 5767b836d78146fdab7d786a1795f8c7
```

Notebook 06 reads UC assets, thresholds, readings and scene_pushes plus the two
MLflow runs. It publishes sixty immutable, audited minute layers per run, each
with a PNG heatmap, thresholds and manifest. Identical preparation reuses push
identities. The viewer artifact is stored in the scenes Volume and both runs;
the desktop files are downloaded artifact copies. There is no local database.

Export downloads the active entry stages' composition files and provenance;
historical publications stay in the Volume/MLflow. All replay minute data travels
in viewer.json. Identical exports preserve USD timestamps to avoid Composer's
base-file refresh notice. Export refuses to overwrite locally edited immutable
USD; use a fresh --output directory when preserving modeling edits. A clean
relocated export with nine USD files reopened both ten-asset stages successfully.

MLflow's wall-clock run duration includes later scene publication sessions.
Use simulation_elapsed_s when discussing simulator runtime, and Step for the
simulated minute on comparison charts.

Launch using [the Kit entry point](kit/README.md). The viewer never queries a
new data service or creates Spark. It changes session opinions while replaying;
published base and state files remain immutable. After editing thresholds,
republish the explicit runs before preparing a new viewer artifact.

## Actual viewport screenshots

Capture frame stages a real Kit screenshot and a lineage receipt in the ignored
.local/omniverse-test/captures folder. For a full preflight, launch with
TWIN_CAPTURE_ALL=1: it renders all sixty minutes of both runs, then returns to
Baseline minute 59. Screenshots include the panel and billboard labels.

After capture, run from LocalUnityCatalog:

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin collect-captures --run-ids 5767b836d78146fdab7d786a1795f8c7 7a617dc8b34b41f98b02725e04db4944
```

Notebook 07 checks each PNG checksum and receipt against its scene_pushes row,
stores it in the UC scenes Volume, logs it on the originating MLflow run, and
updates capture_path. Under scene/runs/<run>/<push>, heatmap.png is the CPU
preview; viewport.png is the actual Kit screenshot, with viewport_receipt.json.
Camera-specific captures retain immutable paths. Notebook 07 refreshes the
governed viewer artifact's audit metadata; repeat export_viewer.py to download
it. Re-ingestion skips already committed receipts. Transfer of a desktop
capture inbox to a real Databricks Volume is **UNTESTED**; notebook 07 accepts
capture_dir as a native Volume path there.

Executed end-to-end artifact verification from LocalUnityCatalog:

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin validate-viewer --run-ids 5767b836d78146fdab7d786a1795f8c7 7a617dc8b34b41f98b02725e04db4944
```

This retrieved and checked all 120 minute publications against UC audit rows,
composed USD colours, immutable base checksums and actual Volume/MLflow PNGs.
After capture preflight, relaunch without TWIN_CAPTURE_ALL for a clean take:
Kit's capture plugin can show an SDK performance warning after 100 captures.

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
   passed locally through the desktop Kit entry point; Kit streaming remains
   deferred to M5.
   [Omniverse test instructions](docs/OMNIVERSE.md) describe the prepared portable
   snapshots and the current Composer setup route.

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
