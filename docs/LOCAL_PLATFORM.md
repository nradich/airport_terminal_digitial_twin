# Local platform discovery

## Verification status

Discovery on 2026-11-09: the airport repository was cloned successfully and is
empty upstream. Docker Desktop was started and existing stopped containers were
restarted without recreation. UC, MLflow, Jupyter, UI, storage and database are
healthy. Live discovery and M0 capability tests passed.

## Live verified findings

- UC returns dbx_cuda and the cudf_processing payment tables, registered as
  EXTERNAL PARQUET at s3://payments/payments_local_v1_seed42/.... This schema
  currently contains no Volumes. Its tables were not modified.
- Jupyter requires the configured token and uses /jupyter/. Authenticated status
  and kernelspec requests returned 200. The service exposes local-cpu and
  local-gpu. A newly started local-cpu kernel reports Python 3.12.3 with no spark,
  dbutils, or mlflow globals. pyspark and delta are not installed.
- MLflow 3.17.0 uses /mlflow/: /health returns 404, /mlflow/health returns 200.
  The client at http://mlflow:5000/mlflow listed four experiments. An existing
  finished run's confusion_matrix.json artifact was downloaded successfully
  (129 bytes). No existing run or artifact was modified.
- UC storage-root.models is file:/data/registry, with authorization disabled.
  Server and notebooks share local-uc_registry-data at /data.
- MLflow's registry client at uc:http://server:8080 successfully read the existing
  dbx_cuda.cuml_agentic_payments.agent_behavior registered model. No model was
  changed; model training/registration for the twin remains deferred to M5.
- Running notebooks use image local-uc-demo:0.1.0 and bind code from the
  gpu-demo and workspace worktrees beneath LocalUnityCatalog/.local/worktrees.
  The server also mounts configuration from the workspace worktree. The root
  compose.yaml is not an exact record of the installed containers.

Reported before M0: preserve the installed services and add compose.spark.yaml
with a separate Python 3.11 service on port 8889. Local tracking defaults to the
verified prefixed URI. Existing 3.12 RAPIDS services are not recreated.

## Configuration-only findings (not live verification)

Source: the adjacent LocalUnityCatalog checkout, compose.yaml and ui/services.cjs.

| Service | Desktop URL | Container URL / configuration |
| --- | --- | --- |
| Workspace | http://localhost:3000 | UI gateway proxies Jupyter and MLflow |
| UC metadata | http://localhost:8080/api/2.1/unity-catalog | http://server:8080/api/2.1/unity-catalog |
| Tracking | http://localhost:5000/mlflow | http://mlflow:5000/mlflow |
| Jupyter | http://localhost:8888/jupyter/ | notebooks:8888/jupyter/ |
| Registry | Not separately published | uc:http://server:8080 |

Jupyter uses a token supplied by the platform's ignored .env; the workspace
gateway keeps it server-side. UC authorization is disabled in this single-user
localhost lab. Never commit credentials or log the token.

MLflow metadata uses the existing platform PostgreSQL service; artifacts use
RustFS S3. UC model files use a persistent shared /data/registry mount. Application
code must not connect directly to metadata databases or treat object snapshots
as an alternative database.

The existing notebook image uses Python 3.12 and RAPIDS. Its checked-in startup
does not inject spark or dbutils. The new Python 3.11 Spark environment must be
separate. Source notebook support, Delta previews, and experiment comparison are
deferred until after airport M3.

## Required live evidence before M0

Container image/version and mounts; effective URL prefixes; authenticated
notebook status and kernels; available Spark globals; existing UC objects;
Volume metadata and backing paths; MLflow experiments and retrievable artifacts.
M0 contract tests subsequently verify writes using uniquely named disposable
objects, not existing user data.

## M0 result

The separate service on port 8889 uses Python 3.11.14, Spark 4.2.0, Delta 4.4.1,
and UC connector 0.7.0. Live contracts returned `1 passed, 1 warning in 13.41s`:
persistent external Delta and a UC view read from a fresh SQL session; Volume
bytes round-tripped; MLflow artifact upload and retrieval matched. All temporary
catalog objects were removed. The pandas 3.x warning is confined to the platform
environment; airport dependencies pin pandas 2.x. Existing RAPIDS containers were
not recreated.

## After M3: verified filming integration

Workspace Notebooks now targets the new Spark service through the additive
overlay. Python source notebooks open, execute and save through the authenticated
gateway. The airport kernel uses its pinned uv environment and platform Spark.
Ordinary .ipynb behavior remains available; source notebooks store code/Markdown,
not execution output metadata.

Workspace Experiments plots real paginated metric histories for two selected
runs and renders the logged PNG via a bounded same-origin proxy. Both were
verified in the browser. Catalog Delta preview returns 50 rows and all six typed
reading columns; the existing payment preview also returned 50 rows through
Spark. Preview inputs/results and execution are bounded. The platform checkout's
docs/airport-filming.md records exact limits and the large-Parquet-file limitation.
