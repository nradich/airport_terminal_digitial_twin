# Decisions

- 2026-11-09: Approved implementation is M0, M1, M2, M3, filming integration,
  then M4. M5 is deferred. No remote push or deployment is authorized.
- M0 is minimal and gated by live discovery. Existing RAPIDS Python 3.12 remains
  untouched; new Spark compute and airport code target Python 3.11.
- sensor_readings uses value_num DOUBLE and value_str STRING. Exactly one is
  populated according to the metric type. flights includes run_id. Views are
  isolated by explicit run_id.
- Default simulation: eight gates, two zones, seed 42, sixty one-minute samples.
  Timestamps are deterministic; baseline and delay_A4 use the same start.
- Qualified SQL function integration has a 30-minute active-work timebox after
  M0. Govern colour/status in latest_state if the attempt fails; keep M1 moving.
- State publications are immutable and content-addressed, with explicit run IDs
  and idempotent audit entries. Base geometry is never changed by a push.
- Mark unexecuted commands and unavailable remote validation UNTESTED. Never
  claim a milestone passed without its required evidence.
- Live discovery found prefixed MLflow/Jupyter URLs and containers owned by
  other worktrees. M0 uses an additive Compose overlay and does not recreate
  those services. Local Delta tables will be UC-registered external Delta on
  shared persistent storage; real Databricks uses managed Delta tables. This
  difference is setup configuration in the adapter, never a compute fork.
- M1 native SQL function attempt returned
  `[MISSING_CATALOG_ABILITY.CREATE_FUNCTION] Catalog dbx_twin does not support
  CREATE FUNCTION`. The capability is absent in the stock UC Spark catalog.
  The attempt completed well inside the 30-minute cap; no custom JVM evaluator
  was added. latest_state contains the canonical governed severity/colour SQL;
  gate_health aggregates its severity. No function placeholder was created.
- The local runner reads bundle local defaults; existing environment settings
  win. Native notebook widgets carry the same configuration remotely. Downstream
  tasks receive the originating run ID explicitly, without searching recent runs.
- Managed notebook environments may omit Git metadata. Require an exact
  TWIN_GIT_SHA in that case, before starting an MLflow run. Bundle git_sha carries
  that value; the empty default deliberately cannot produce an unidentified run.
- M4 separates offline packaging/schema checks from authenticated workspace
  validation. The latter failed for missing credentials; M4 remains incomplete.
  No deployment or upload was performed during M4 preparation. The user later
  authorized pushing the airport and platform feature branches; both were pushed.
- Desktop inspection uses a separate Kit --exec entry point with session-only
  preview lighting and native snapshot buttons. This avoids unreliable automated
  text entry in Composer's custom file picker and preserves the user's unsaved
  original stage in a separate window. Published USD files stay unchanged.
- Film preparation adds assets.asset_name without changing display_name, prim
  paths or immutable base geometry. Existing non-null names are preserved.
  The notebook library publishes versioned viewer JSON to the scenes Volume and
  originating MLflow runs. Desktop JSON files are artifact copies, not a side
  database. Kit uses CPU-only presentation/reader modules and native rendering;
  it never creates Spark or duplicates governed severity rules.
# Film publication and capture lineage

Every replay minute has its own content-addressed publication and scene_pushes
row (run_id, scenario, step, USD path). The viewer artifact embeds those audit
rows; the panel and session metadata use the selected minute's push, never an
implicit latest run. Preparation preserves historical publications and adds
nullable metadata columns without rewriting their immutable USD.

CPU heatmaps are previews, not renderer screenshots. Actual Kit screenshots
are staged with checksummed receipts and ingested by notebook 07, which validates
UC lineage before storing Volume/MLflow artifacts and updating capture_path.
This keeps Kit data access thin and avoids a GPU dependency in airport compute.
The local preflight captures all 120 minute publications. Remote capture-inbox
transfer remains UNTESTED. No new platform API or database is introduced.
