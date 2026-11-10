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
environment setting chooses baseline or delay_A4; the default is baseline.
The Airport snapshots panel has Baseline/Delay A4, Replay, play/pause, a minute
scrubber, Overview/A4 cameras and Film mode. Its data is the versioned UC/MLflow
artifact prepared by notebook 06; see [FILMING.md](../FILMING.md). The default
scenario is baseline. Switching animates session-layer colours over 1.5 seconds
with a distance-based ripple from A4. It does not reopen or mutate base geometry.

The entry point opens the explicit snapshot and its saved camera/light layer,
checks ten asset prims, and overlays camera-facing governed asset labels. Published
layer files are checksummed before and after setup. It does not save the stage
or change base geometry. The title's asterisk can reflect session-only preview
lighting/camera changes.

The earlier desktop snapshot acceptance passed: baseline rendered green A4; delayed A4 rendered
red, with amber security. Both native buttons were exercised. Logs contain
AIRPORT_VIEWER_READY for both scenarios. The original unsaved New Stage was
left open in its own window. Film-ready acceptance is recorded separately in
[FILM_READY.md](../docs/FILM_READY.md).

For capture preflight, set `$env:TWIN_CAPTURE_ALL = '1'` before the same launch
command. Remove that environment variable for ordinary interactive use. Capture
frame stages PNG receipts; notebook 07 ingests them through the shared library
into the Volume/MLflow. No data-platform access is implemented in Kit. Kit needs
the repository's src and kit folders (resolved by open_scene.py); desktop Kit's
own Python runtime is separate from Python 3.11 airport compute.

For a fresh immutable export, set TWIN_VIEWER_DIRECTORY to its absolute folder
before launch. The default remains .local/omniverse-test. The configured folder
supplies viewer.json, both USD entry stages and its own captures directory;
existing edited exports are not overwritten. For this rehearsal the fresh folder
is .local/omniverse-provenance. Use that captures folder explicitly when ingesting.
