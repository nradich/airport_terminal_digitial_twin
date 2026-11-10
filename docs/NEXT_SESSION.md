# Continue on 2026-11-10

Airport repo: C:\Users\nicho\Desktop\Workspace\Databricks\airport_term_digital_twin
Branch: codex/airport-twin. Five film implementation steps committed locally;
no remote push or deployment. LocalUnityCatalog code was not changed in this task.
Its untracked demo_audio.wav and docs/demo-plan.md were left untouched.

## Stable checkpoint

Labels, governed legend/run details, A4 ripple, minute replay, saved cameras,
Film mode and per-minute publication lineage are implemented. Databricks-only
data access remains in airport_twin modules through the existing platform adapter.
Read [FILM_READY.md](FILM_READY.md) for evidence and limitations, and
[FILMING.md](../FILMING.md) for tested commands and the 60-second shot list.

| Scenario | MLflow run | Final push prefix |
| --- | --- | --- |
| baseline | 5767b836d78146fdab7d786a1795f8c7 | de41b2323d41 |
| delay_A4 | 7a617dc8b34b41f98b02725e04db4944 | 79eaf0fcd0e4 |

Each run has sixty audited minute publications. All 120 actual viewport PNGs
were retrieved and checked against UC/MLflow with validate-viewer. Final unit/live
integration suite: 33 passed; Ruff clean. Re-ingestion skips committed captures;
baseline final push retry reused its identity. History and base geometry remain.

The ordinary Composer launch was left running on Baseline/Overview, Film mode on,
with larger labels. It reached RTX ready; final desktop inspection was interrupted
by physical Escape, so do not assume foreground/focus. Preserve the older unsaved
New Stage window. Docker's eight services were running at handoff.

## First checks tomorrow

1. Inspect the existing Airport snapshots window. Test direct scrubbing, Play/
   Pause and Open in MLflow on the final build. Replay, scenario switching,
   cameras and Film mode were already exercised. Compare the two explicit runs
   above in native MLflow at http://localhost:5000/mlflow/.
2. Run the 60-second shot list. Capture an A4 close-up if wanted: Capture frame,
   then the documented collect-captures command. Actual PNG ingestion is explicit;
   CPU-only pushes produce heatmap previews immediately.
3. For a fresh desktop artifact, run the documented export_viewer.py command.
   For new data/thresholds, republish runs then prepare-viewer with explicit IDs.
   Do not reset volumes or truncate tables to prepare a take.

Launch from airport .local/kit-app-template with the command in kit/README.md.
Use ordinary mode (TWIN_CAPTURE_ALL unset) for filming; the all-frame preflight
can leave a Kit SDK performance warning in the status bar after 100 screenshots.
Desktop Kit uses its own runtime; Spark stays in Python 3.11 and RAPIDS is untouched.

Evidence logs are in LocalUnityCatalog/.local: film-tests-final.log,
film-publications-prepare.log, film-retry.log, film-capture-ingest-final.log,
film-capture-retry.log and film-validate-viewer.log. Ignored desktop artifacts and
captures are in airport .local/omniverse-test. Do not commit those generated files.

Remote Databricks execution/authenticated validation and capture-inbox transfer
remain UNTESTED. M4 remains incomplete. M5 App/forecaster/Kit livestream deferred.
