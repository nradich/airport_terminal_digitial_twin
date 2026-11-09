"""CPU-rendered top-down heatmap using the exact OpenUSD asset layout."""

from __future__ import annotations

from pathlib import Path

from airport_twin.scene.layout import shape


def render_heatmap(manifest: dict, scenario: str, destination: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Patch, Rectangle

    fig, ax = plt.subplots(figsize=(14, 5), dpi=160)
    fig.patch.set_facecolor("#0F172A")
    ax.set_facecolor("#0F172A")
    ax.add_patch(Rectangle((-9, -7.5), 60, 15, facecolor="#263449", zorder=0))
    states = {s["asset_id"]: s for s in manifest["states"]}
    pax = {
        s["asset_id"]: s["value_num"]
        for s in manifest["metric_states"]
        if s["metric"] == "pax_count"
    }
    for asset in manifest["assets"]:
        layout = shape(asset)
        x, y, _ = layout.position
        w, h, _ = layout.size
        state = states[asset["asset_id"]]
        patch = (
            Circle((x, y), w / 2) if layout.cylinder else Rectangle((x - w / 2, y - h / 2), w, h)
        )
        patch.set_facecolor(state["colour"])
        patch.set_edgecolor("#CBD5E1")
        patch.set_linewidth(1.2)
        ax.add_patch(patch)
        label = asset["display_name"].replace(" checkpoint", "").replace(" claim", "")
        if asset["asset_id"] in pax:
            label += f"\n{int(pax[asset['asset_id']])} pax"
        ax.text(x, y, label, ha="center", va="center", fontsize=10, weight="bold", color="#0F172A")
    ax.text(21, 0, "CONCOURSE A", color="#CBD5E1", ha="center", fontsize=15, weight="bold")
    ax.set_title(
        f"AIRPORT TWIN  /  {scenario}\nFinal simulated minute · run {manifest['run_id'][:8]}",
        color="white",
        fontsize=16,
        loc="left",
        pad=18,
    )
    ax.set_xlim(-21, 63)
    ax.set_ylim(-17, 17)
    ax.set_aspect("equal")
    ax.axis("off")
    legend = ax.legend(
        handles=[
            Patch(facecolor=c, label=s)
            for s, c in [("OK", "#22C55E"), ("WARN", "#F59E0B"), ("CRITICAL", "#EF4444")]
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.06),
        ncol=3,
        frameon=False,
        labelcolor="white",
    )
    legend.set_zorder(10)
    fig.savefig(destination, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
