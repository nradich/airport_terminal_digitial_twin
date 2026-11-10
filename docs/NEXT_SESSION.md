# Next session — Azure proof remains gated

Airport: cursor/m7-browser-twin-pr-41e6. Implementation checkpoint 5caf847.
Platform: codex/airport-platform-prereqs, latest 046b3e7; three commits ahead of
its remote. No push, new PR or deployment was performed. The unrelated platform
files demo_audio.wav and docs/demo-plan.md remain untouched.

## What to open

- Browser twin: http://localhost:8000. Click a gate or its gate-table button.
- Tight provenance: explanation, five rows, rule, run/push and source versions;
  Details collapsed. Compare in MLflow opens the explicit filming pair.
- MLflow: http://localhost:5000/mlflow/ (experiment /Shared/airport-twin).
- Start tomorrow with ../PREFLIGHT.md; evidence is in REHEARSAL.md.

## Current filming identities

Baseline: 5767b836d78146fdab7d786a1795f8c7.
Delay: 7a617dc8b34b41f98b02725e04db4944.
Comparison: 798f7f7331c6f1c2ae5768c4278ab6c7031e5b63375ff51a82873424ccef605b.
Fresh viewer artifact: viewer/5da303a3f3cbf2c43a8b04d726e860a66d056a78e2a2617e43b6f96912ba22c2/viewer.json.
New v2 publications freeze SQL, source versions, publisher Git/package/source hash;
four native Delta dataset inputs are logged to each run. Older publications remain.

Fresh Composer files were exported to .local/omniverse-provenance and round-trip
checked with OpenUSD. Existing .local/omniverse-test files and unsaved desktop
stages were not overwritten. The current Kit launcher still uses omniverse-test:
loading the fresh export into the desktop renderer is a remaining manual rehearsal
step, not a claimed GPU pass for the new bundle. Historical M5 GPU evidence stands.

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

M4/M7e remain incomplete until real authenticated execution passes. CI is prepared
but not activated remotely. PR #1 needs review after an authorized push of the new
commits; the gateway changes need a separate scoped PR after approval. M6 and props
stay on hold. Keep 365-day retention and no VACUUM/history truncation.
