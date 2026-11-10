"""Saved presentation cameras in a separate USD layer; base geometry is immutable."""

from pxr import Gf, Usd, UsdGeom, UsdLux


def story_layer_bytes() -> bytes:
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    for name, display, eye, target, projection in (
        ("Overview", "Overview", (21, -45, 65), (21, 0, 1), "orthographic"),
        ("A4CloseUp", "Gate A4 close-up", (53, -7, 18.5), (42, 10, 2), "perspective"),
    ):
        camera = UsdGeom.Camera.Define(stage, "/World/Film/" + name)
        camera.GetPrim().SetDisplayName(display)
        camera.CreateProjectionAttr(projection)
        camera.CreateClippingRangeAttr(Gf.Vec2f(0.1, 1000))
        if projection == "orthographic":
            # Orthographic aperture is measured in tenths of a stage unit.
            camera.CreateHorizontalApertureAttr(900)
            camera.CreateVerticalApertureAttr(450)
        else:
            camera.CreateHorizontalApertureAttr(36)
            camera.CreateVerticalApertureAttr(20.25)
            camera.CreateFocalLengthAttr(40)
        transform = (
            Gf.Matrix4d()
            .SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(0, 0, 1))
            .GetInverse()
        )
        camera.AddTransformOp().Set(transform)
    UsdLux.DomeLight.Define(stage, "/World/Film/Light").CreateIntensityAttr(700.0)
    return stage.GetRootLayer().ExportToString().encode("utf-8")
