# Milestone evidence

## M0 — passed

Platform commit: 1fb4063 on codex/airport-platform-prereqs.
Separate Python 3.11.14/Spark 4.2.0 service; existing RAPIDS preserved.
Live UC/Delta/view/Volume/MLflow contracts: 1 passed in 13.41s; one platform pandas
3.x warning. Fresh notebook kernel confirmed the injected Spark 4.2.0 session.
See the platform checkout's docs/spark-platform.md for executed commands.

## M1 — passed

Idempotent setup, typed numeric/categorical readings, deterministic simulator,
run-scoped persistent views, explicit run handoff, MLflow params/step histories.
Executed notebook path: 00_setup → 02_simulate → 04_validate through Jupyter.
Run: e606cc269c9e41c19b61f6f6499a2f39, /Shared/airport-twin, experiment 5.
Validated ten assets, eight flights, 2,520 readings, 42 latest metric rows,
and eight gate-health rows. Simulation/write/metrics elapsed: 6.644s.
pytest including live view edge tests: 15 passed in 16.98s. Ruff: all checks passed.
Run commands appear in README.md and were executed.

Risks: the stock local catalog does not implement SQL functions, so governed
view SQL is active. Source notebook editing, Delta previews, and Workspace
Experiments comparison are deferred until after M3. Remote execution is UNTESTED.

## M2 — passed

Executed 00 → 01 → 02 → 03 → 04 for baseline run
9b5f798c2b114d9ea1622bb0e5b8d8f4. Ten asset prims compose correctly in the Volume.
Base SHA256: 2e1c47c7217e4311c025e0577db893e546c085e8f59184ea5017a98bfe9b021c.
Repeated push reused ID
4f09c469c8fde457fe78c79617c29477e3cd3fd8b80a49f44332eb91131aa67f.
The manifest contains all 42 metric states and source Delta versions. The base
remained unchanged. Simulator/write/metrics elapsed: 5.818s.

Unit tests: 18 passed, 1 integration test deselected, in 15.23s. Includes USD
round-trip, correct asset paths/colours, root-layer units/axis, immutable writes,
and recovery from an injected audit failure after file publication. Ruff clean.
Executed commands are in README.md.

Risks: Volume publication currently assumes one scene writer; remote FUSE behavior
and opening in an actual Omniverse Kit application are UNTESTED. Kit streaming is
a deliberate unsupported stub. MLflow scene artifacts and PNGs arrive in M3.

## M3 — passed

Both scenarios executed 00 → 04. Baseline:
fec2d8ef61b94c4590b2ac3f624aae22. Delay:
8c9da58a294f4cbab4255799f79b34ec. Both use seed 42 and the same start timestamp.
All four metric histories contain steps 0..59. Each run's scene bundle, PNG,
thresholds and manifest were downloaded from the live MLflow server; checksums,
relative USD composition and image decoding passed. The PNGs were visually
inspected: A4 is green with 6 people in the final baseline frame and red with
213 people in the delayed frame. Peak A4 population: 126 versus 213.

Native MLflow Model training → Compare → peak_pax_A4 was verified in the browser.
Both scenario curves render by Step and the comparison shows identical seeds,
timestamps and thresholds. Simulator/write/metrics times: 5.183s and 4.761s.
pytest including live SQL and MLflow: 20 passed in 27.45s. Ruff clean.

Artifacts preserve `scene/terminal_base.usda` and
`scene/runs/<run>/<push>/terminal_state_<run>.usda` so downloaded bundles compose.
Run commands are in README.md. Native MLflow is http://localhost:5000/mlflow/.
Earlier M1/M2 runs predate complete artifact logging; use these M3 runs for filming.

Risks: remote Databricks remains UNTESTED; Workspace UI enhancements follow M3.

## Filming integration — passed

Added source-notebook editing, a pinned airport kernel, bounded Spark previews,
Workspace metric comparison and PNG viewing. The browser verified source
execution and saving, typed Delta sample data, run comparison retained while
opening details, the actual delayed-run heatmap and governed view SQL display.
The existing payment Parquet preview still returns 50 rows through Spark.

UI build: 18 tests and 3 gateway tests passed, production TypeScript compiled.
Platform regression suite: 5 passed; Ruff clean for airport and platform code.
Jupyter metadata-only/source-save responses were corrected after a live save
test, with regression coverage. Ordinary .ipynb behavior is preserved. Source
files retain code/Markdown boundaries but do not persist outputs or arbitrary
notebook metadata. FILMING.md records the tested workflow and service selection.

Risks: large Parquet input sets over the 16 MiB whole-file staging cap now fail
explicitly instead of range-sampling. Delta input sizes are labeled estimates.
The original RAPIDS service is unchanged; the overlay routes Workspace Notebooks
to the airport service. Remote execution remains UNTESTED.
