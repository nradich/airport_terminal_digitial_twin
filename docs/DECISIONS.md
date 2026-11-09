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
  No deployment, upload or remote push is authorized or performed.
