# Platform requests

## M0 prerequisites

- Separate Python 3.11 Spark kernel connected to UC; preserve Python 3.12 RAPIDS.
- Persistent Delta tables and views, Volume read/write, MLflow artifact round-trip.
- Gate airport M1 on live contract tests for these capabilities.

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
