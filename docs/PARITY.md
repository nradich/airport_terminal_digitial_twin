# Platform parity

| Capability | Local | Databricks | Status |
| --- | --- | --- | --- |
| Compute | Separate Python 3.11 Spark notebook environment | Serverless environment 2 | M0 pending |
| Tables/views | UC OSS + Spark/Delta | Native UC + Delta | Live discovery pending |
| Volumes | UC metadata-resolved shared persistent mount | /Volumes/catalog/schema/volume | Adapter pending |
| Tracking | Existing MLflow server | Workspace MLflow | Live verification pending |
| Notebook parameters/results | Headless runner context | Widgets/task values | Adapter pending |
| SQL scalar functions | Timeboxed qualified invocation attempt | Native UC functions | May fall back to governed view SQL |
| Bundle execution | Local runner; no emulated deployment API | Native bundles | Remote validation UNTESTED |

All platform differences belong in thin adapters. The simulator and USD authoring
must not contain local/remote forks or GPU dependencies.

Local Delta storage uses UC-registered EXTERNAL Delta locations on the existing
shared /data volume, with all reads/writes by three-level name. Databricks setup
uses managed Delta without LOCATION. No table data is stored in a UC Volume.
The scenes Volume has its own non-overlapping registered directory.
