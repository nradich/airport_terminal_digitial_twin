# Desktop snapshot viewer

USD Composer / Kit 110.4.1 runs outside Databricks on the desktop RTX GPU.
The airport notebooks remain CPU-only. This is a published-snapshot viewer;
KitMessageTransport and automatic streaming updates remain deferred.

composer-template.toml contains the verified NVIDIA template replay inputs.
See ../docs/OMNIVERSE.md for installation and export details.

From .local/kit-app-template in PowerShell, these commands were executed:

```powershell
$env:TWIN_VIEWER_SCENARIO = 'baseline'
.\repo.bat launch -n airport.composer.kit -- --exec C:/Users/nicho/Desktop/Workspace/Databricks/airport_term_digital_twin/kit/open_scene.py
```

open_scene.py resolves the exported USD folder relative to its repository. The
environment setting chooses baseline or delay_A4; the default is delay_A4.
The Airport snapshots window has Baseline and Delay A4 buttons. Save any modeling
edits separately before switching; these buttons reopen the exported snapshots.

The entry point opens the explicit snapshot, adds a light in the session layer,
frames the concourse, checks ten asset prims and verifies A4 status. Published
layer files are checksummed before and after setup. It does not save the stage
or change base geometry. The title's asterisk can reflect session-only preview
lighting/camera changes.

Live desktop acceptance passed: baseline rendered green A4; delayed A4 rendered
red, with amber security. Both native buttons were exercised. Logs contain
AIRPORT_VIEWER_READY for both scenarios. The original unsaved New Stage was
left open in its own window. Ruff passed for kit and the airport Python sources.
