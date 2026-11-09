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
