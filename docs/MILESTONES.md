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
