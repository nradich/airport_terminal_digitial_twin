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

## M4 — prepared, incomplete

Added local/dev bundle targets, a serial serverless environment-2 job, configurable
namespace/tracking/package settings, packaged SQL, explicit widget/run-ID handoff,
standalone SQL rendering, Make aliases and offline dependency preparation.
Local configuration is consumed by the local runner, not a deployment emulator.

Executed with Docker Compose in the platform checkout:

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync ruff check src tests notebooks scripts
docker compose -f compose.yaml -f compose.spark.yaml exec -T -e TWIN_RUN_INTEGRATION=1 spark-notebooks uv run --no-sync pytest -q
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv build --wheel
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks python scripts/prepare_offline.py
```

Final output: Ruff all checks passed; 23 pytest tests passed in 25.81s.
Formatting: 28 files already formatted. Both full notebook pipelines passed again:
baseline f3e57101b9144577a2cc7e4b5c9ce388 and delayed
b642c81185ff463485248242448fe4f9. Each validated 2,520 readings, eight flights,
42 latest-state rows, eight gates, composed USD and retrieved tracking artifacts.

The wheel and all 89 runtime dependency wheels installed with --no-index into
an isolated Python 3.11 environment. Package/SQL imports, deterministic simulation,
USD code and dependency checks passed. The official CLI schema accepts the bundle
configuration. Generated Databricks SQL was rendered, not executed remotely.

Authenticated databricks bundle validate --strict -t dev was attempted with CLI
1.25.0 and failed because default credentials are unavailable. Real workspace
validation and execution are **UNTESTED**; M4 is not complete. No push, upload or
deployment occurred. PORTABILITY.md records commands, restrictions and remaining
native-function, Volume filesystem and serverless dependency compatibility risks.

## Desktop Omniverse inspection — passed

The user authorized desktop Composer setup and feature-branch pushes. NVIDIA
Kit App Template b8e9f2e4 generated airport.composer using the checked-in playback
configuration. Kit 110.4.1 built successfully in 104.29s and initialized D3D12 /
RTX Real-Time 2.0 on the desktop RTX 5060 Ti. SDK installation stays outside the
Spark/RAPIDS environments; standard NVIDIA caches are documented in OMNIVERSE.md.

The initial screenshot showed Composer's default New Stage, before airport data
was loaded. Automated text input into its custom file picker was unreliable.
kit/open_scene.py now opens explicit exported snapshots using Kit --exec, adds
session-only preview lighting, frames the concourse and exposes two native
snapshot buttons. The original unsaved stage was kept open in a separate window.

Live GPU verification showed all ten assets, green A4 in baseline and red A4 plus
amber security in delay_A4. Both buttons and a return to baseline were exercised.
The Stage panel identified /World/Concourse_A/Gate_A4 on the red geometry.
Kit logs recorded AIRPORT_VIEWER_READY for both scenarios. The script checked
asset counts/status and unchanged published-layer file checksums. Ruff passed
for src, tests, notebooks, scripts and kit. Published base geometry was unchanged.

These remain final-minute snapshots, with simple box/cylinder geometry. Timeline
replay, live Kit messaging and physics behavior are not implemented by this test.
Authenticated Databricks validation/execution remains UNTESTED and M4 incomplete.

## M7 — browser twin (local complete; cloud incomplete)

Local M7a–M7d deliverables are on `codex/airport-twin` (no push). Gateway tip
`718a7eb` on LocalUnityCatalog `codex/airport-platform-prereqs`. Playwright against
the live App is **8 passed**, including the post-filming pause-during-blend and
resize tests. See `docs/M7.md` for commands, timings and commit IDs.

M7e local packaging (`app/app.yaml`, `app/requirements.txt`,
`resources/airport.app.yml`) is present. Authenticated
`databricks bundle validate --strict -t dev` failed for missing default
credentials — same class of blocker as M4. Cloud App / SQL connector execution,
lean non-Spark App base, GPU 30 FPS desktop target, Dev OAuth/resource grants,
restricted-network install and deployed WebGL remain **UNVERIFIED**. M7e is not
complete until Nick supplies Databricks auth and a warehouse ID.
