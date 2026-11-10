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
