# Platform parity

| Capability | Local | Databricks | Status |
| --- | --- | --- | --- |
| Compute | Separate Python 3.11 Spark notebook environment | Serverless environment 2 | Local verified; remote UNTESTED |
| Tables/views | UC OSS + Spark/Delta | Native UC + Delta | Local persistent-table/view contracts passed |
| Volumes | UC metadata-resolved shared persistent mount | /Volumes/catalog/schema/volume | Local round-trip passed; remote UNTESTED |
| Tracking | Existing MLflow server | Workspace MLflow | Local histories/artifact retrieval passed |
| Notebook parameters/results | Headless context or explicit interactive dictionary | Widgets/task values | Local browser/runner verified; remote UNTESTED |
| SQL scalar functions | Governed latest_state SQL fallback | Native UC functions | Local capability rejected; fallback verified |
| Bundle execution | Local runner; no emulated deployment API | Native bundles | Remote validation UNTESTED |

All platform differences belong in thin adapters. The simulator and USD authoring
must not contain local/remote forks or GPU dependencies.

Local Delta storage uses UC-registered EXTERNAL Delta locations on the existing
shared /data volume, with all reads/writes by three-level name. Databricks setup
uses managed Delta without LOCATION. No table data is stored in a UC Volume.
The scenes Volume has its own non-overlapping registered directory.

M1 verified fallback: the local catalog rejects CREATE FUNCTION with
MISSING_CATALOG_ABILITY.CREATE_FUNCTION. latest_state owns the SQL expression.
On Databricks the same setup attempts the native function and uses it after a
qualified boundary check. UC OSS view replacement also requires drop/create;
setup skips identical definitions, but a changed definition has a brief gap.

The dev bundle uses serverless environment version 2 and the same packaged
library/SQL as local execution. Configuration widgets and explicit task-value
parameters are implemented but cloud execution is UNTESTED. The local target
supplies runner defaults only, with no emulated deployment API. Offline CLI-schema
checks pass; authenticated validation failed for missing credentials. See
PORTABILITY.md for wheelhouse evidence and the outstanding real-workspace proof.

Film-ready data follows the same adapters: notebook 06 queries qualified UC
tables/views, publishes replay layers and a viewer artifact to the scenes Volume
and MLflow, and scripts/export_viewer.py downloads those artifacts. Kit consumes
the files and shared pure presentation functions; it contains no table/MLflow
client or Spark engine. Local URLs translate the tracking container hostname to
localhost; Databricks URLs resolve the configured SDK workspace host.

Actual PNG capture requires the desktop RTX renderer. Kit stages receipts only;
notebook 07 verifies run/scenario/step/push identity and ingests files through
VolumeTransport and the configured MLflow client. Local staging is a file inbox,
not business-data storage. For cloud use, transfer that inbox to a UC Volume and
set capture_dir; that transfer, remote notebook execution and real-workspace
artifact routing are UNTESTED. CPU heatmap publication remains available without
an RTX renderer. Film-ready local acceptance is in FILM_READY.md.

M7 Browser App: local FastAPI uses an internal bearer-authenticated named-read
Spark gateway, fixed to dbx_twin.airport, with 5000 rows/2 MiB/30s/two-query limits.
It never sends SQL from the browser or starts Spark in the App. Dev uses the same
trusted query builders through the Databricks SQL connector and App OAuth, and
Files API for Volume downloads (cloud access UNVERIFIED). Local files resolve
through UC Volume metadata and a read-only /data mount. MLflow remains the only
run/metric/artifact source. Audited replay pins Delta versions and thresholds;
current snapshots remain an explicitly separate API. No local bundle deployment
API is emulated. No VACUUM, log truncation or manual source-file deletion is
allowed during audit. App packaging declares least-privilege bindings in
`resources/airport.app.yml` and runtime pins in `app/requirements.txt` /
`app/app.yaml`; authenticated workspace validation is still UNVERIFIED.

Local Spark UC-view binding workaround: stock UC OSS view expansion drops Spark
named SQL parameters and raises UNBOUND_SQL_PARAMETER for `:name` binds against
views such as latest_state/gate_health. The LocalUnityCatalog twin-query gateway
adapter therefore encodes only registry-validated restricted scalars after
parameter checks (strings may not contain quotes, backslashes or SQL punctuation).
Canonical airport SQL templates stay unchanged. Databricks/dev uses the SQL
Connector's native named binds. See LocalUnityCatalog docs/query-gateway.md;
platform history gateway commit 718a7eb.
