# Local rehearsal and Azure readiness

## Post-reboot check — 2026-11-11

Started Docker Desktop and restored existing volumes. Corrected NEXT_SESSION.md:
ordinary restart uses `compose start`, preserving the workspace-specific MLflow
prefix and notebook image. The earlier root-only `up` instruction recreated the
base MLflow service without /mlflow; its workspace overlay was reapplied, restoring
the existing /mlflow route and local-uc-demo:0.1.0 notebook runtime. No datasets,
historical publications or environments were rebuilt.

Actual App reads recovered all five saved runs, including the 120-minute baseline.
The existing film.mjs walkthrough passed: baseline peak 126, delayed peak 213,
both GLBs rendered, five-row provenance verified, native comparison opened with
both intended runs, and cached minute-10 scrub measured 1.3 ms in software Chromium.
Fresh screenshots/evidence are in app/frontend/.local/filming (ignored). The
desktop browser also showed the audited minute-59 delayed run and 213 >= 180.
Azure remains UNVERIFIED and no deployment was performed.

Airport and gateway pushes/PR updates were authorized on 2026-11-10. No Azure
deployment. Azure execution remains UNVERIFIED. Airport working branch:
cursor/m7-browser-twin-pr-41e6. Gateway review branch: codex/airport-query-gateway,
based on the separate LocalUnityCatalog codex/airport-platform-prereqs branch.

## Verified implementation checkpoint — 2026-11-10

- CPU: **52 passed, 2 deselected, 14 upstream deprecation warnings in 29.07s**.
- Live browser: **10 passed (57.9s)**, including provenance, exact native MLflow
  comparison, paused blend, resize, image failures and both cancellation races.
- Synthetic browser contracts: **2 passed (17.5s)**. These are explicitly not live integration.
- Ruff: clean. TypeScript and frontend build passed.
- Disposable parity notebook 11 passed: persistent Delta table/view from a fresh
  session, Volume bytes and retrieved MLflow artifact matched, colour boundaries
  passed using the verified local view-SQL fallback. Scratch schema and run were
  cleaned up; none of the twin tables or historical source files were deleted.
- Official CLI 1.25 schema validates local/dev including the App resource.
  The validator now handles Unicode property patterns rather than skipping them.
- Staged dev catalog/schema override to parity_catalog/parity_schema passed;
  restored the default dbx_twin.airport artifact afterward.
- Clean image: Python **3.11.14**, package installed under /app/.venv, Spark absent.
  App code/frontend are installed from dist/app; the desktop source mount was removed.

## Commands actually executed

From LocalUnityCatalog (all compose commands include compose.yaml and compose.spark.yaml):

```powershell
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin contracts
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync airport-twin prepare-comparison --run-ids 5767b836d78146fdab7d786a1795f8c7 7a617dc8b34b41f98b02725e04db4944
docker compose -f compose.yaml -f compose.spark.yaml exec -T spark-notebooks uv run --no-sync python scripts/package_app.py --target dev --skip-frontend
docker compose -f compose.yaml -f compose.spark.yaml -f compose.twin-app.yaml build twin-app
docker compose -f compose.yaml -f compose.spark.yaml -f compose.twin-app.yaml up -d --no-deps twin-app
```

The skip-frontend build followed an actual npm typecheck/build in the Node image.
The full package command (including npm ci/build) subsequently passed from a clean
Git archive of 5caf847 in app/Builder.Dockerfile (Node 22, uv 0.10.2, Python 3.11.14).
The isolated staged App imported without Spark and its cached offline reinstall
passed. A separately exported **98-wheel** closure installed into a fresh
environment with Docker network disabled: OFFLINE_APP_IMPORT_OK.
Gateway contracts passed **2/2**. Public GitHub CI passed on the pushed Composer
adapter commit cf2b814; synthetic checks never connect to the desktop.

## Explicit comparison

Baseline: 5767b836d78146fdab7d786a1795f8c7; delay: 7a617dc8b34b41f98b02725e04db4944.
Volume record: comparisons/798f7f7331c6f1c2ae5768c4278ab6c7031e5b63375ff51a82873424ccef605b/comparison.json.
It is logged to both originating runs. No latest-run inference is used. The browser
link opens native MLflow with the exact two IDs and peak_pax_A4 values 126/213.
Docker browser tests translate localhost:5000 traffic to mlflow:5000 inside their
test network; the desktop-facing product URL remains localhost:5000.

## Remaining Azure gate

Workspace URL/region, UC metastore, warehouse ID, experiment ID, App principal,
OAuth/grants, native comparison route and cloud WebGL/Volume behavior are UNVERIFIED.
The dev comparison link stays unavailable until a verified workspace route template
is configured; it never substitutes a guessed URL. See ../PREFLIGHT.md.
M4/M7e remain incomplete until authenticated validation and deployed acceptance pass.
M6 and external props remain on hold. Gateway review is now PR #9 in nradich/local_uc.

## Final rehearsal follow-up

Both browser projects passed together: **12 passed (1.3m)**. Offline GLB validation
reported zero errors, warnings, infos and hints. The current filming script discovers
the explicit pair, captures the five-row explanation with Details closed, and opens
the native 126/213 comparison; cached scrub measured **2 ms** in software Chromium.
Native desktop GPU FPS is not measured by that test. Stills are in
app/frontend/.local/filming (ignored), including browser-provenance.png and
mlflow-comparison.png.

Read-only 120-step measurement passed in **3.768s**: each page had 600 SQL states
and 240 metric points; actual response sizes 186799/186107 bytes. Raw 5040-row
read hit the unchanged limit and nonexistent Delta version returned HTTP 410.
The script was passed on stdin into the clean App; there is no source mount.

Both new Composer exports composed to the recorded colours through OpenUSD.
They are in a fresh .local/omniverse-provenance folder; existing edited exports and
desktop windows were not replaced. Fresh RTX Composer reload passed on 2026-11-10:
Baseline Overview at minute 59 showed green A4 and peak 126; switching to Delay A4
finished at red A4, peak 213, one critical gate, and push b2a3d6003732. The A4 camera
and all ten labels were visually verified. Focused viewer/camera tests: **2 passed
in 19.20s**. TWIN_VIEWER_DIRECTORY selected the fresh export without replacing edited
exports. GPU FPS and transition timing were not benchmarked in this walkthrough.
New publication b2a3d60037327432d0610251b2d557b204a104d6039bf93fc0a35a1063070594
records publisher 5caf84733760f5a67508ba409199352034d58446 and frozen rule
1c952bfaca272d5ca77737a2126dad41d4fa9dbf3938509cd4d75405b6e89558;
the originating delayed run has **four native Delta dataset inputs**.

Authenticated CLI validation was attempted again: failed for missing default
credentials. This is an actual failure, not a passed cloud validation. See ignored
.local/dev-validate.log. Offline schema validation passed including App resources.
App POST /api/runs returned **405** and its sole data mount is **/data RW=false**;
actual cloud service-principal enforcement remains UNVERIFIED.
