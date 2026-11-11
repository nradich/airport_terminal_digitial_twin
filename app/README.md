# Browser twin (three.js)

The current App installs from a staged artifact rather than a desktop source mount.
`uv run python scripts/package_app.py --target dev` builds the shared wheel,
frontend, locked Python 3.11 dependency closure and resolved app.yaml in dist/app.
This full command passed in the clean-checkout Builder.Dockerfile rehearsal.
Dockerfile installs that artifact into a lean CPU runtime without Spark.

Use root bundle variables for catalog/schema/experiment and real warehouse/experiment
IDs for dev resource bindings. `app/app.yaml` accepts an optional **verified**
Databricks comparison URL template with baseline_run_id/delay_run_id/experiment_id
placeholders; absent a verified route, the cloud comparison link is unavailable.
Local native MLflow routing is verified. No deployment or push has been performed.

The primary action is Compare in MLflow. Clicking a gate or its table button
explains its five SQL sensor rows against the exact publication. Details stays
collapsed. See [preflight](../PREFLIGHT.md) and [evidence](../docs/REHEARSAL.md).

Audited replay of Concourse A in the browser. Same governed Delta data as the
Omniverse path — two renderers.

## M7 polish

![3/4 overview with lifted labels and badge under the title](../docs/images/m7/overview-34.png)

*3/4 overview — lifted gate labels, status badge under the title.*

![Gate A4 close-up in critical state](../docs/images/m7/a4-closeup.png)

*Gate A4 close-up — crit at minute 59 of the delay_A4 replay.*

![Delay / ripple filming beat](../docs/images/m7/browser-ripple.png)

*Delay / ripple filming beat — A4 critical with the ripple transition in view.*
