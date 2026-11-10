# Test the published twin in Omniverse

The first test opens published USD snapshots in a desktop USD Composer app.
Databricks simulates and governs the state; Composer renders the resulting USD.
Live Kit messaging remains deferred. These snapshots show the final simulated
minute; playing the viewport timeline does not replay the sixty-minute run.

## Prepared files

Verified local hardware: NVIDIA GeForce RTX 5060 Ti, 16,311 MiB VRAM,
driver 610.88. USD Composer is now installed and launched using Kit 110.4.1.
The desktop renderer initialized on this GPU with D3D12 / RTX Real-Time 2.0.
No driver change was required.

The ready-to-open folder is:

```text
C:\Users\nicho\Desktop\Workspace\Databricks\airport_term_digital_twin\.local\omniverse-test
```

Open baseline.usda or delay_A4.usda at the top of that folder. Keep the entire
folder together: the short entry files compose the downloaded state layers,
which in turn compose their immutable terminal_base.usda. Opening only the base
does not show the run's governed colours. export_manifest.json records run/push
IDs and base checksums. Build/export outputs remain ignored by Git.
The adjacent .local/omniverse-test.zip packages the complete folder. Extracting
it into a different temporary directory and reopening both entry stages passed:
RELOCATED_USD_OK, ten asset colours each, A4 ok versus crit.

Both bundles were downloaded from live MLflow and verified with OpenUSD:
state/base checksums, all asset paths and composed colours passed. Source runs:

| Entry file | Run ID | Expected final A4 |
| --- | --- | --- |
| baseline.usda | 5767b836d78146fdab7d786a1795f8c7 | green, ok, 6 people |
| delay_A4.usda | 7a617dc8b34b41f98b02725e04db4944 | red, crit, 213 people |

## Verified Composer installation

NVIDIA provides USD Composer through its
[Kit App Template](https://github.com/NVIDIA-Omniverse/kit-app-template), as
described in the [Composer build guide](https://docs.omniverse.nvidia.com/composer/latest/how-to-build.html).
The template checkout is pinned by the recorded source commit
b8e9f2e4f2930d19e87e3702d4eeaf00d9846676. BUILD (RELEASE) SUCCEEDED in
104.29 seconds. SDK downloads and first-start shader compilation are separate
from the airport's warm-run timing budget.

From the airport repository in PowerShell:

```powershell
git clone --depth 1 https://github.com/NVIDIA-Omniverse/kit-app-template.git .local/kit-app-template
Copy-Item kit/composer-template.toml .local/kit-app-template/airport-composer.toml
Set-Location .local/kit-app-template
.\repo.bat template replay airport-composer.toml
.\repo.bat build
.\repo.bat launch -n airport.composer.kit
```

These individual commands were executed. The saved playback uses NVIDIA's
source-verified template replay format and explicit short app/extension names.
An initial interactive attempt appended defaults and exceeded Windows' path
limit; its partial output was preserved in source_failed_template. The corrected
app is airport.composer with setup extension airport.setup.

NVIDIA's standard caches are C:\\packman-repo and
%LOCALAPPDATA%\\ov\\data\\exts. The generated app lives beneath
.local/kit-app-template. The Kit app uses a separate desktop runtime; airport
Spark notebooks remain CPU-only and the existing RAPIDS environment is unchanged.

## Airport viewport acceptance — pending scene loading

The current default New Stage is the Composer environment, not the airport.
The following checks remain UNTESTED until the prepared airport file is opened.

1. In Composer choose File → Open and open the prepared baseline.usda.
2. Select /World/Concourse_A in the Stage panel and press F to frame the scene.
   Expect eight gate boxes, security and baggage geometry, and the floor.
3. If the viewport is dark, enable Camera Light in the Viewport Render Mode menu.
4. Inspect /World/Concourse_A/Gate_A4: twin:asset_id is GATE_A4 and twin:status
   is ok. The gate should appear green.
5. Open delay_A4.usda. A4 should appear red and twin:status should be crit.
   Confirm the base geometry and asset positions match baseline. Security also
   changes from green to warning amber. Compare the downloaded heatmap.png in
   each publication folder with the viewport.
6. Check the app's log for unresolved sublayers. Missing geometry usually means
   the state file was separated from its relative base path. Retain the complete
   export folder when copying it to another machine.

NVIDIA references: [File menu](https://docs.omniverse.nvidia.com/composer/latest/menu_file.html),
[viewport navigation](https://docs.omniverse.nvidia.com/composer/latest/skills/viewport-nav.html),
[Camera Light](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/rtx-renderer_camera-light.html).

This validates file publication and viewer interoperability. Automatic refresh
from future scene pushes requires the next local Kit integration; the existing
KitMessageTransport deliberately raises NotImplementedError.
