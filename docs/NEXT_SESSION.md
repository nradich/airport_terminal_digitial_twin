# Film-ready checkpoint — 2026-11-10

Airport repo: C:\Users\nicho\Desktop\Workspace\Databricks\airport_term_digital_twin
Branch: codex/airport-twin. Five film implementation steps plus verification fixes kept locally;
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
integration suite: 36 passed; Ruff clean. Re-ingestion skips committed captures;
baseline final push retry reused its identity. History and base geometry remain.

The updated Composer viewer is left on Delay A4/Gate A4 close-up, Film mode on.
Direct scrubbing, Play/Pause, paused-frame capture and the MLflow button passed.
Cancellation during a blend now settles exact colours and audit identity together;
pure regression tests cover it. Preserve the older unsaved New Stage window and
other pre-existing viewer windows. Docker's eight services remain running.

## Next work

1. Record the 60-second shot list. Native MLflow comparison was rechecked: both
   explicit runs' complete peak_pax_A4 histories are visible by step, 126 vs 213.
   Start at Baseline/Overview/minute 59, then Delay A4, close-up and MLflow.
2. A fresh A4 close-up and paused frames were captured and logged. For new takes,
   use Capture frame then collect-captures. Actual PNG ingestion is explicit;
   CPU-only pushes produce heatmap previews immediately.
3. For a fresh desktop artifact, run the documented export_viewer.py command.
   For new data/thresholds, republish runs then prepare-viewer with explicit IDs.
   Do not reset volumes or truncate tables to prepare a take.

Export now keeps identical USD timestamps and refuses to overwrite locally
edited immutable USD. A clean export needs only nine USD files for both entry
compositions; replay minute data is in viewer.json. All historical scene files
and screenshots remain in UC Volume/MLflow. Use a new --output folder for a fresh
export when preserving model edits.

Launch from airport .local/kit-app-template with the command in kit/README.md.
Use ordinary mode (TWIN_CAPTURE_ALL unset) for filming; the all-frame preflight
can leave a Kit SDK performance warning in the status bar after 100 screenshots.
Desktop Kit uses its own runtime; Spark stays in Python 3.11 and RAPIDS is untouched.

Evidence logs are in LocalUnityCatalog/.local: film-tests-final.log,
film-publications-prepare.log, film-retry.log, film-capture-ingest-final.log,
film-capture-retry.log and film-validate-viewer.log. Latest evidence uses the
film-resume-* prefix (tests-final, export-bounded, relocated, captures, validate).
Ignored desktop artifacts and
captures are in airport .local/omniverse-test. Do not commit those generated files.

Remote Databricks execution/authenticated validation and capture-inbox transfer
remain UNTESTED. M4 remains incomplete. M5 App/forecaster/Kit livestream deferred.
