# Restart handoff — 2026-11-11

Airport: cursor/m7-browser-twin-pr-41e6. Visible UI uses American spelling and
now includes replay-availability checks, duration labels and clean failure recovery.
Airport PR #1 contains the updates; consult its latest checks before merging:
https://github.com/nradich/airport_terminal_digitial_twin/pull/1.
Platform checkout: codex/airport-platform-prereqs, latest 046b3e7. The same three
gateway/App commits were pushed as codex/airport-query-gateway, with green CI:
https://github.com/nradich/local_uc/pull/9 (base codex/airport-platform-prereqs).
Both PRs need human review; neither was merged. No Azure deployment was performed.
Unrelated platform files demo_audio.wav and docs/demo-plan.md remain untouched.

## Resume after the computer restarts

Start Docker Desktop and wait for its Linux engine. From
C:\Users\nicho\Desktop\Workspace\LocalUnityCatalog, start the existing containers
without recreating their workspace-specific runtime configuration:

```powershell
docker compose -f compose.yaml -f compose.spark.yaml -f compose.twin-app.yaml start
docker start local-uc-gateway-1
docker compose -f compose.yaml -f compose.spark.yaml -f compose.twin-app.yaml ps
```

Post-reboot SQL reads, all five saved runs, both filming scenes, five-row gate
provenance and native MLflow comparison passed on 2026-11-11. The commands above
were exercised. Existing named Docker volumes hold Delta/UC, scenes and MLflow state. Keep those volumes;
do not use down -v or prune them. Ignored .local/twin-app.env supplies the existing
gateway secret and is already on disk; never commit its contents.

The previous bare root `up -d` instruction was incomplete: recreating workspace
services from root compose.yaml drops MLflow's /mlflow prefix and selects the base
notebook image. On this desktop the existing workspace overlay is
.local/worktrees/gpu-demo/compose.workspace.yaml. Recovery used the existing file:

```powershell
docker compose -f compose.yaml -f .local/worktrees/gpu-demo/compose.workspace.yaml up -d --no-deps mlflow notebooks
```

This restored the /mlflow route and the prior local-uc-demo:0.1.0 notebook image.
No source environments or persistent data were rebuilt. Prefer `start` for the
next ordinary reboot; a new-machine workspace recreation still requires its
workspace overlay and is not covered by the airport-only compose files.

Open http://127.0.0.1:8000/ for the App, http://localhost:3000 for the workspace,
and http://localhost:5000/mlflow/ for MLflow. Allow Spark time to warm up before
refreshing the App. If QUERY_FAILED recurs, inspect twin-query logs before retrying.

On 2026-11-11 the gateway's Java process stopped answering while the Python HTTP
health endpoint still reported healthy. Restarting only twin-query restored SQL
reads (HTTP 200) and the full browser scene/provenance panel. Cause of the Java
exit is UNVERIFIED. Follow-up: make readiness detect a dead Spark connection and
clear stale UI evidence when a run change fails. Do not substitute current data
for missing audited history.

## What to open

- Browser twin: http://127.0.0.1:8000/. Click a gate or its gate-table button.
- Tight provenance: explanation, five rows, rule, run/push and source versions;
  Details collapsed. Compare in MLflow opens the explicit filming pair.
- MLflow: http://localhost:5000/mlflow/ (experiment /Shared/airport-twin).
- For an authorized Azure session start with ../PREFLIGHT.md; evidence is in REHEARSAL.md.

## Current filming identities

Baseline: 5767b836d78146fdab7d786a1795f8c7.
Delay: 7a617dc8b34b41f98b02725e04db4944.
These filming runs are 60 minutes, steps 0–59; peak A4 populations are 126/213.
The selector now includes durations and disables runs without a complete coherent
audited replay. Legacy baseline 958ff1aa has mixed source versions (59 snapshots
under one identity and one under another); do not merge or overwrite those audit
records. It remains visible as replay unavailable. Failed selections clear old
evidence and disable playback rather than using a previous run's replay ID.
The 120-minute test run is baseline 7cf727f3ceee423594894181a9574fdb (the last
dropdown option, steps 0–119). Its complete audited replay was verified available
on 2026-11-11. It has legacy publication metadata, not the newer frozen-rule/
publisher fields; it is not the explicit filming comparison pair.
Comparison: 798f7f7331c6f1c2ae5768c4278ab6c7031e5b63375ff51a82873424ccef605b.
Fresh viewer artifact: viewer/5da303a3f3cbf2c43a8b04d726e860a66d056a78e2a2617e43b6f96912ba22c2/viewer.json.
New v2 publications freeze SQL, source versions, publisher Git/package/source hash;
four native Delta dataset inputs are logged to each run. Older publications remain.

Fresh Composer files are saved in .local/omniverse-provenance and round-trip
checked with OpenUSD. RTX desktop verification passed: Baseline Overview, Delay
A4 red/213, all ten labels and A4 close-up. Existing .local/omniverse-test exports
and other desktop stages were not overwritten. Set TWIN_VIEWER_DIRECTORY to the
absolute .local/omniverse-provenance directory before using the existing Kit
launcher; see kit/README.md. The fresh viewer.json and both entry USD files are
already on disk; no scene re-publication is required merely to reopen them.

## Azure session order

1. Record workspace URL/region, metastore, namespace, warehouse/experiment IDs and
   actual App principal. Confirm serverless Python 3.11 and Apps availability.
2. Configure CLI auth; validate dev with the real IDs and exact selected git_sha.
3. Run notebook 11 disposable contracts in the approved catalog (no resets).
4. Deployment requires explicit approval. Generate fresh cloud baseline/delay IDs;
   publish complete replay sets and prepare-comparison with those exact IDs.
5. Observe the real native comparison URL and configure the verified template in
   app/app.yaml; cloud routing is deliberately unavailable until verified.
6. Check SP grants/denied writes, Volume/MLflow retrieval, UC lineage and full replay.

M4/M7e remain incomplete until real authenticated execution passes. CI is active
and passed on both PRs. Airport PR #1 and gateway PR #9 need review. M6 and props
stay on hold. Keep 365-day retention and no VACUUM/history truncation.
