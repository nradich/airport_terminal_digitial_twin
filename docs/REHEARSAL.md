# Local rehearsal and Azure readiness

No remote push, PR creation or deployment. Azure execution remains UNVERIFIED.
Airport working branch: cursor/m7-browser-twin-pr-41e6. The local gateway remains
on the separate LocalUnityCatalog codex/airport-platform-prereqs branch.

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
The full package command (including npm ci/build) is prepared for CI and must be
rehearsed in a clean combined build environment before claiming that path tested.
Gateway contracts passed **2/2**. Public GitHub CI activation is UNVERIFIED because
the workflow has not been pushed; synthetic checks never connect to the desktop.

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
M6 and external props remain on hold. Gateway review is local only; no PR was opened.
