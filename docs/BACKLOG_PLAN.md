# Airport twin — backlog and four-minute filming plan

Story: one governed Delta layer drives Composer and the browser. A coloured gate
is traceable to sensor values, thresholds, SQL, a publication and an MLflow run.
S = about half a day; M = 1–3 days; L = several days+, excluding access delays.

| Item | Priority / effort | Adds to story | Dependencies / risk | Workspace | Proof |
|---|---|---|---|---|---|
| M6 passenger journey | Hold; M browser MVP / L both renderers | Passenger decision from conditions | Queue length is not calibrated waiting time; missing coffee/restroom signals and as-of deadlines | Cloud proof later | Seed/deadline/uncertainty tests; no future leakage; parent-run linkage |
| USDCraft props | Hold first film; S intake / M USD / L general GLB conversion | Governed external geometry | Materials, transforms, meshes, licence packaging, performance | Intake local; Volume grants later | Hashes/licence, complete references, USD/GLB validation, stable gate IDs |
| M0/M4 | Now readiness; before filming cloud proof; S/M | Actual Databricks execution | Local M0 complete; real parity remains unverified | Required to close M4 | Fresh-session Delta/views, Volume/MLflow round-trips, rule parity, retention, authenticated validate |
| M7 deployment prep | Now; M | Portable browser twin | Packaging, configuration, grants, stale scrub and adapter errors | Fixes local; acceptance cloud | Clean-room install/startup; read-only and failure tests |
| CI/gateway | Now preparation; S/M | Reproducibility | Live fixtures need services; gateway changes need scoped review | No Azure for core checks | CPU/build/package/browser contracts; separate live integration |
| Provenance MVP | Now; M | Why A4 is red | Frozen vs current evidence; legacy limitations | Core local; native UC links later | Five rows, explanation/rule/run/push/versions, historical failure handling |

## Order and scope
1. Build/install the shared wheel and frontend as one locked Python 3.11 App;
   fix startup, binding/configuration, scrub race and cloud adapter contracts.
2. Tight provenance panel: explanation, five rows, colour rule, run/publication/
   Delta versions; primary Compare in MLflow; hashes/code/SQL in collapsed Details.
3. Explicit governed comparison pair in the Volume, referenced by both MLflow runs;
   no latest-run guessing. Verify native comparison routes per platform.
4. CI/preflight/local rehearsal. Prepare a gateway-only review locally; opening
   a PR or pushing still requires approval. See ../PREFLIGHT.md.
5. Azure readiness/validate/dev contracts; deployment only after explicit approval.
   Regenerate cloud runs and version references, then rehearse before filming.

## Tracking gaps and fixes
- Freeze canonical scoring/colour SQL, rule ID and publisher identity in new manifests.
- Include source versions/rules in new publication identity; retain legacy artifacts.
- Keep replay sets separate by source, rule, threshold, assets, geometry and story identity.
- Log Delta dataset inputs to MLflow; manifests describe generated file relationships.
- Distinguish application-recorded provenance from native UC lineage. Local native
  colour function is unavailable: governed SQL fallback is real, not a placeholder.
- Do not claim legacy publications recorded SQL/code identity they did not record.

## Held work
Journey MVP: CPU Monte Carlo over a frozen twin minute and governed policy; log a
separate parent-linked MLflow run and Delta summaries. Read-only browser panel
first, Kit snapshot later. Scheduled departure minus 15 minutes is the explicit
default deadline unless an as-of estimate exists. No animated paths in MVP.

USDCraft revision eaf0237cbe8887fdad71f02bbf2a397edc8822f3 declares Apache-2.0;
2,004 objects. Three candidate chair/cart/bench folders total ~0.99 MB before
conversion; no kiosk category found. Preserve manifest/licence in a Volume,
ingest metadata to Delta and track chosen/derived hashes in MLflow. Keep props
separate from the ten operational assets. Conversion/performance UNVERIFIED.
[Pinned source](https://huggingface.co/datasets/nvidia/USDCraft-10K/blob/eaf0237cbe8887fdad71f02bbf2a397edc8822f3/README.md).

## Storyboard — about four minutes
| Time | Beat | Tracked components |
|---|---|---|
| 0:00–0:25 | Catalog: assets, typed readings, thresholds | UC tables and Delta history |
| 0:25–1:00 | MLflow first: seed/start/scenario and 126 vs 213 histories | Runs, params, Git identity, metrics |
| 1:00–1:30 | Composer baseline, explicit minute | USD, run/push and captured artifacts |
| 1:30–2:00 | Same minute in browser; orbit | Volume GLB, governed colours, publication |
| 2:00–2:30 | Delay A4 ripple and earlier replay minute | Delta versions, thresholds, exact-step metrics |
| 2:30–3:25 | Click A4: 213 ≥ 180, five rows, rule and versions | Publication-specific provenance; Details closed |
| 3:25–4:10 | One click Compare in MLflow, then artifacts | 126/213 comparison, USD/GLB/PNG; native UC lineage if verified |

Keep M4/M7e incomplete until authenticated/cloud acceptance actually passes.
