# Film-ready implementation evidence

No remote push or deployment is authorized for this work. Each numbered step
is committed locally on codex/airport-twin.

## 1. Labels

Added the nullable asset_name column and backfilled A1–A8, Security and Baggage
through platform Spark. Existing non-null names, display names, prim paths and
run history are preserved. Label data uses the shared geometry layout and
rejects missing/duplicate names. Kit renders constant-screen-size, camera-facing
labels from the published artifact rather than guessing names.

23 CPU/USD unit tests passed (2 integration tests deselected); Ruff clean.
Live 00_setup → 06_prepare_viewer succeeded for the explicit filming runs
5767b836d78146fdab7d786a1795f8c7 and 7a617dc8b34b41f98b02725e04db4944.
The viewer JSON was published to the scenes Volume and both MLflow runs, then
downloaded with complete USD composition trees. Desktop verification follows
after the five implementation steps; cloud execution remains UNTESTED.

## 2. Legend and run information

Added a canonical SQL-derived palette, current governed thresholds, categorical
severity explanations, MLflow run name/short ID, exact-step values for the four
requested metrics, and a public run URL. Missing/duplicate/nonfinite metric steps
fail rather than borrowing another step. The native panel has an Open in MLflow
button and read-only copyable URL. Cloud links use the documented workspace
/ml/experiments route; TWIN_MLFLOW_PUBLIC_URI can override public routing.

Four pure presentation tests passed. Live notebook preparation read five threshold
rows and all sixty steps of four metrics from each explicit MLflow run and
published bundle 654111c6. It rejects a stale publication when current thresholds
do not match its recorded snapshot. Desktop panel verification follows step 5.

## 3. Ripple and replay

Shared SQL templates now score complete historical minute frames directly from
the run-filtered sensor_readings table; no severity logic is copied into Kit.
Both filming runs exported sixty complete frames with ten assets each. Their
final A4 states remain ok versus crit. The controller blends in linear RGB over
1.5 seconds, staggers by distance from A4, and adds a transient neutral glint so
the wave is visible on unchanged healthy gates. Final colours are exact governed
values; the glint never changes stored status or data.

Added scrubber, replay and play/pause using exact per-step MLflow values. Seven
presentation/timeline tests passed; the complete suite including live SQL and
MLflow passed: 30 tests in 33.38s. Ruff clean. The versioned replay bundle was
published and downloaded successfully. Desktop playback verification follows.

## 4. Story cameras and Film mode

Saved Overview and Gate A4 close-up as native USD Camera prims in a separate,
content-addressed story layer with neutral lighting. The layer is published to
the scenes Volume and both MLflow runs; exported entry stages compose it without
changing terminal_base.usda. A USD round-trip test passed and verified that the
Overview frustum contains all ten asset centres.

Added native camera buttons and Film mode. Grid, axes, selection guides, camera/
light guides and performance HUD visibility use the installed Kit version's
verified per-viewport settings. Turning Film mode off restores previous values.
Ruff clean. Local camera-bundle preparation passed; final desktop inspection
follows step 5. Remote rendering remains UNTESTED.

## 5. Per-minute audit and actual screenshots

Added additive scenario/step/preview_path/capture_path audit columns and migrated
legacy final-frame metadata without rewriting their USD. All sixty minute frames
per run now have their own verified, immutable USD, CPU heatmap and exact threshold/
Delta-version/base/state manifest in the scenes Volume and originating MLflow run.
The panel and session metadata select the minute's scene_pushes identity.

Notebook 07 checks actual renderer PNG receipts against UC, stores captures in
the Volume/MLflow, updates capture_path, and refreshes the governed viewer artifact.
The desktop inbox is ignored staging. Notebook 08 retrieves all scene artifacts
and verifies each minute's audit, composed USD, PNG checksum/dimensions and base.

Actual local results:

- Full pytest, including live SQL and MLflow: 33 passed in 45.57s; fourteen upstream
  Matplotlib/Pyparsing deprecation warnings. Ruff clean.
- Two renderer preflights each captured 120 frames. The second enlarged labels
  and panel text and replaced unsupported threshold glyphs with readable ASCII.
- Ingestion linked all 120 publications. Re-ingestion: captures=0, skipped=240,
  publications=0. Refreshed bundle efcd249e8219ccedc89908ec2b7674125e7bc61406eee6e60ce7a22fe9e9a652.
- validate-viewer: verified_publications=120, both explicit filming runs.
- Baseline step-59 retry reused de41b2323d41 and its immutable files/audit identity.
- Native Baseline/Delay switching, travelling colour transition, Overview/A4
  close-up, replay through 0–59 and Film-mode pane restoration were exercised.
  Final delayed A4 is critical; peak 213 versus baseline 126.
- Last ordinary viewer launch reached RTX ready in 22.399s. GPU capture preflight
  completed 120 frames by 54.080s including startup; simulator timing is unchanged.

The first capture attempt exposed Sdf.Path/string conversion and was corrected.
An initial native window activation timed out; a fresh viewer recovered. The
original unsaved New Stage was preserved. Two older Composer windows remain open.
The final desktop inspection was stopped by the user's physical Escape key;
no further desktop inputs were sent. Direct scrub, play/pause and Open in MLflow
button interaction on the final build remain to check tomorrow; their data paths
and interpolation are tested. The native MLflow comparison was verified in prior
work, not repeated during this final pass.

Real Databricks execution, authenticated bundle validation, remote capture-inbox
transfer and other Kit versions remain UNTESTED. Actual renderer PNG attachment
uses the explicit capture/ingestion step; a CPU-only push logs its heatmap preview
immediately. No Kit streaming, GPU compute in airport code, remote push or deploy
was introduced. The local SQL-function fallback remains documented and active.
