# Azure session preflight — one page

Record each check as **PASS / FAIL / UNVERIFIED**, with UTC time and evidence.
Local rehearsal evidence: `docs/REHEARSAL.md`. No credentials belong in this file.

## Target and identity
- [ ] Workspace URL/name: **UNVERIFIED**; Azure region: **UNVERIFIED**.
- [ ] UC metastore: **UNVERIFIED**; namespace: `dbx_twin.airport` (configurable).
- [ ] Selected Git SHA and CLI profile target the intended workspace.
- [ ] Azure budget/credits and feature availability confirmed by owner.

## Compute and resources
- [ ] UC enabled; serverless notebook environment 2 reports Python 3.11.
- [ ] Small SQL warehouse ID recorded; starts and answers a read query.
- [ ] Databricks Apps enabled; App service principal identified.
- [ ] Scenes Volume and `/Shared/airport-twin` experiment path/ID resolved.
- [ ] Wheel/locked dependencies available; restricted-network installation tested.

## Permissions — verify using each actual identity
- [ ] App: warehouse CAN_USE; USE CATALOG/SCHEMA; SELECT on required tables/views;
      scenes READ_VOLUME; experiment CAN_READ; function EXECUTE if needed.
- [ ] Publisher: required object creation, table modification, Volume writes and MLflow logging.
- [ ] Presenter: Catalog, experiment comparison/artifacts and lineage visibility.
- [ ] App HTTP writes denied; actual SP data/Volume write privileges absent.

## Artifact and dev contracts
- [ ] Self-contained App starts without source mounts or developer PYTHONPATH.
- [ ] Launcher port and target configuration resolve correctly.
- [ ] Disposable contracts: qualified Delta write/read; persistent view in fresh
      session; Volume byte round-trip; MLflow upload/retrieval; colour-rule edges.
- [ ] Five twin tables report 365-day data/log retention; **no VACUUM**.
- [ ] `databricks bundle validate --strict -t dev` passes with real IDs and exact git_sha.
- [ ] Cloud SQL unavailable-history response is HTTP 410; exact-image fallback works.

## Demo rehearsal
- [ ] Fresh cloud baseline/delay runs have explicit IDs and matching seed/start/duration.
- [ ] Complete audited replay sets published; browser/Composer agree at selected minute.
- [ ] A4: **213 passengers ≥ critical threshold 180**, five sensor rows, rule and versions.
- [ ] Compare in MLflow opens the exact two runs; peak_pax_A4 **126 vs 213** visible.
- [ ] Native Databricks comparison URL verified; no guessed route or implicit latest run.
- [ ] USD/GLB/PNG hashes and MLflow links agree; native UC lineage verified if filmed.

**GO/NO-GO:** authenticated validation is not execution proof. Deployment requires
explicit approval; cloud filming requires deployed contracts and the full rehearsal.
Do not copy local run IDs or Delta version numbers into Azure. Keep unknowns
UNVERIFIED. No remote push, PR creation or deployment is implied by this checklist.
