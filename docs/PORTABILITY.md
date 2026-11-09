# M4 portability status

## Verified locally

- Built airport_twin-0.1.0-py3-none-any.whl using uv on Python 3.11.14. The wheel
  includes library code and all five SQL resources, including the scalar function.
- Exported runtime dependencies from uv.lock and prepared 90 wheels (about
  211 MiB) including the project wheel. SHA256SUMS verifies every file.
- Installed all 90 packages in a fresh Python 3.11 virtual environment using
  --no-index. An isolated interpreter imported the installed wheel, loaded its SQL,
  generated 2,520 deterministic readings and loaded USD code. No Spark, RAPIDS,
  CuPy, or DuckDB package is installed in that environment. Dependency checks pass.
- Downloaded official Databricks CLI 1.25.0 and verified its published asset digest.
  The configuration passes offline validation against that CLI's JSON schema.
- Authenticated bundle validation was attempted and failed because default
  credentials are not configured. It did not pass, and nothing was deployed.

**M4 remains incomplete. Authenticated bundle validation and real-workspace
execution are UNTESTED.** Offline schema validation is not a portability proof.

## Targets and parameters

databricks.yml defines local and dev. Local supplies defaults to the headless
runner; existing environment variables take precedence. It deliberately defines
no Databricks job resources and is not a local deployment-API emulator.

Dev defines a serial serverless job: setup → build_scene → simulate → push_scene
→ validate. All tasks use environment version 2 (Python 3.11). No cluster or GPU
configuration is supplied. A wheel is built during bundle deployment and included
in synchronized files. The dependency path is configurable with package_dependency.

Configurable variables are catalog, schema, experiment, warehouse_id, platform,
tracking_uri, registry_uri, git_sha and package_dependency. warehouse_id is reserved
for SQL editor/future App use; notebook tasks do not require a warehouse.

Bundle configuration passes TWIN_* and tracking settings as notebook parameters.
The thin adapter resolves those widgets into Config, sets the session timezone
to UTC and uses the platform Spark session. The simulator and USD code are shared.
The simulator publishes its MLflow ID with dbutils.jobs.taskValues.set; downstream
tasks receive {{tasks.simulate.values.run_id}} as an explicit parameter. No latest
run lookup or taskValues.get fallback is used.

Set git_sha to the exact commit being deployed. Managed Git folders and deployed
workspace files may not expose .git; TWIN_GIT_SHA is required in that case. Missing
Git identity fails before creating a tracking run rather than logging unknown.

## Restricted outbound access

The prepared local wheelhouse is .local/wheelhouse; the project wheel is also in
dist. These are ignored build artifacts, not a data store or committed dependency
vendoring. scripts/prepare_offline.py regenerates them from the lockfile.

For an offline workspace, upload these artifacts to a governed UC libraries Volume
or permitted workspace files, verify SHA256SUMS, and use a requirements file with
--no-index, --find-links pointing to that wheelhouse, and the project wheel path.
Set package_dependency to a requirements-file reference beginning with -r and its
absolute /Volumes/... or /Workspace/... path. Upload and remote installation are
UNTESTED and were not performed. The staged binary wheels target Linux x86_64,
Python 3.11; validate the target architecture before use.

For a Git folder, select serverless environment 2 and install the wheel using the
notebook Environment pane. Configure TWIN_* widgets, tracking URI databricks,
registry URI databricks-uc, and the exact Git SHA. This interactive cloud workflow
is UNTESTED. No notebook code fork is needed.

## Remaining proof and risks

With an authenticated profile, run bundle validate for dev and review workspace
permissions, dependency-path resolution and serverless environment availability.
Do not deploy or push without the user's explicit approval. After approval, run
both scenarios at the same commit and repeat 00→04 acceptance, including downloaded
artifact composition and final A4 colour comparison.

Native UC function invocation, cloud Volume filesystem publication behavior and
Free Edition runtime dependency compatibility remain UNTESTED. The local SQL
fallback is documented in PARITY.md. When updating a previously deployed wheel,
bump its package version and dependency path to avoid cached serverless packages.

scripts/render_sql.py emits standalone Databricks DDL, idempotent seed MERGEs,
views and the function for SQL editor/MCP use. Rendering was tested; executing
that generated script in a real workspace is UNTESTED. Makefile aliases mirror
the CLI commands; invoking Make itself on this PowerShell host is UNTESTED.

References: [serverless environments](https://docs.databricks.com/aws/en/compute/serverless/dependencies),
[task values](https://docs.databricks.com/aws/en/jobs/task-values),
[Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
