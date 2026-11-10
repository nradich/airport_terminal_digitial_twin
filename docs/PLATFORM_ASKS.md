# Platform requests

## M0 prerequisites

- Separate Python 3.11 Spark kernel connected to UC; preserve Python 3.12 RAPIDS.
- Persistent Delta tables and views, Volume read/write, MLflow artifact round-trip.
- Gate airport M1 on live contract tests for these capabilities.

Implemented and verified in platform commit 1fb4063. The later regression suite
passed all five tests after pinning pandas 2.2.3; the original pandas warning is
resolved. The existing Python 3.12 RAPIDS service remains unchanged.

## Non-blocking SQL function support

Qualified UC-stored SQL scalar functions are not established by the current
configuration. After M0 passes, spend at most 30 minutes of active implementation
and debugging on a tested integration. If unavailable, govern the canonical
colour/status expression in latest_state and record the actual result here.
Do not create a nonfunctional function placeholder.

Verified M1 result: Spark returned MISSING_CATALOG_ABILITY.CREATE_FUNCTION for
the stock UC catalog. Support is still requested, but not a blocker. The active
colour/status expression is governed by the persistent latest_state view.

## After M3, before filming

Databricks source-notebook editing; bounded Spark-backed Delta table previews;
Workspace Experiments metric-history comparison and PNG artifact viewing.

Implemented in platform commit c179221 and verified in the running browser.
Source-notebook editing/execution/saving, bounded Delta and existing payment
previews, two-run metric comparison, PNG viewing and governed view SQL display
all passed. Limits and remaining preview risks are recorded in MILESTONES.md.

## M7 App / cloud (open)

Local twin-query gateway and browser App are verified on this desktop. Still
requested before claiming M7e complete:

- Authenticated `databricks bundle validate --strict -t dev` with a real
  `warehouse_id` and App service-principal OAuth.
- Least-privilege grants matching `resources/airport.app.yml` (warehouse
  `CAN_USE`, scenes `READ_VOLUME`, table/view `SELECT`, `status_colour`
  `EXECUTE`, experiment `CAN_READ`).
- Optional lean non-Spark App base image (local still reuses `local-uc-spark`
  without importing Spark).
- Restricted-network install path and deployed WebGL confirmation.
