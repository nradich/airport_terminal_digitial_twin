"""Camera-facing labels rendered from the governed viewer artifact."""

import omni.ui as ui
from omni.ui import scene as sc


class AssetLabels:
    def __init__(self, viewport_window, rows: list[dict]) -> None:
        self.viewport_window = viewport_window
        self.frame = viewport_window.get_frame("airport_asset_labels")
        with self.frame:
            self.view = sc.SceneView()
            with self.view.scene:
                for row in rows:
                    with sc.Transform(transform=sc.Matrix44.get_translation_matrix(*row["anchor"])):
                        with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                            with sc.Transform(scale_to=sc.Space.SCREEN):
                                widget = sc.Widget(
                                    width=max(108, len(row["text"]) * 22 + 40), height=60
                                )
                                with widget.frame:
                                    with ui.ZStack():
                                        ui.Rectangle(
                                            style={
                                                "background_color": 0xEB24201C,
                                                "border_radius": 5,
                                            }
                                        )
                                        ui.Label(
                                            row["text"],
                                            alignment=ui.Alignment.CENTER,
                                            style={"color": 0xFFFFFFFF, "font_size": 36},
                                        )
        viewport_window.viewport_api.add_scene_view(self.view)

    def destroy(self) -> None:
        self.viewport_window.viewport_api.remove_scene_view(self.view)
        self.view.scene.clear()
        self.frame.clear()
