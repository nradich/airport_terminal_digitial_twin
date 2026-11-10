"""Native Kit controls; data validation and formatting live in airport_twin."""

import webbrowser

import omni.ui as ui

from airport_twin.presentation import run_panel_data


def ui_colour(value: str) -> int:
    red, green, blue = (int(value[i : i + 2], 16) for i in (1, 3, 5))
    return 0xFF000000 | blue << 16 | green << 8 | red


class SnapshotPanel:
    def __init__(self, legend: dict, on_scenario) -> None:
        self.window = ui.Window("Airport snapshots", width=450, height=490)
        self.run_url = ""
        with self.window.frame:
            with ui.VStack(spacing=6):
                with ui.HStack(spacing=6, height=32):
                    ui.Button("Baseline", clicked_fn=lambda: on_scenario("baseline"))
                    ui.Button("Delay A4", clicked_fn=lambda: on_scenario("delay_A4"))
                self.title = ui.Label("Airport concourse", height=22)
                self.identity = ui.Label("", height=20)
                self.metric_labels = [ui.Label("", height=22) for _ in range(4)]
                with ui.HStack(height=26, spacing=8):
                    for name in ("ok", "warn", "crit"):
                        with ui.HStack(spacing=5):
                            ui.Rectangle(
                                width=16,
                                height=16,
                                style={"background_color": ui_colour(legend["colours"][name])},
                            )
                            ui.Label(name)
                for row in legend["thresholds"]:
                    ui.Label(row["text"], height=19, style={"font_size": 13})
                ui.Label(" · ".join(legend["categorical"]), height=20, style={"font_size": 13})
                ui.Button(
                    "Open in MLflow", height=28, clicked_fn=lambda: webbrowser.open(self.run_url)
                )
                self.url = ui.StringField(read_only=True, height=24)
                self.status = ui.Label("Preparing scene", height=32, word_wrap=True)

    def update(self, run: dict, step: int) -> None:
        data = run_panel_data(run, step)
        self.title.text = data["title"]
        self.identity.text = data["identity"]
        for label, text in zip(self.metric_labels, data["metric_text"], strict=True):
            label.text = text
        self.run_url = data["url"]
        self.url.model.set_value(self.run_url)
