from pxr import Gf, Usd, UsdGeom

from airport_twin.data import ASSETS
from airport_twin.layout import shape
from airport_twin.scene.cameras import story_layer_bytes


def test_saved_story_cameras_round_trip_and_overview_contains_all_assets(tmp_path):
    path = tmp_path / "terminal_story.usda"
    path.write_bytes(story_layer_bytes())
    assert path.read_bytes() == story_layer_bytes()
    stage = Usd.Stage.Open(str(path))
    overview = UsdGeom.Camera(stage.GetPrimAtPath("/World/Film/Overview"))
    close = UsdGeom.Camera(stage.GetPrimAtPath("/World/Film/A4CloseUp"))
    assert close.GetPrim().GetDisplayName() == "Gate A4 close-up"
    assert overview.GetProjectionAttr().Get() == "orthographic"
    assert close.GetProjectionAttr().Get() == "perspective"
    assert UsdGeom.GetStageUpAxis(stage) == "Z"
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1
    camera = overview.GetCamera(Usd.TimeCode.Default())
    frustum = camera.frustum
    for row in ASSETS:
        asset = dict(
            zip(("asset_id", "asset_type", "zone", "prim_path", "display_name"), row, strict=True)
        )
        layout = shape(asset)
        center = Gf.Vec3d(*layout.position)
        assert frustum.Intersects(center), row[0]
