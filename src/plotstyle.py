"""Shared look for every figure, so the report reads as one set.

Colours are used in this fixed order and always mean the same thing:
    series 1 (blue)   -> the full graph / first series
    series 2 (orange) -> the graph without merges / second series
"""

import matplotlib

matplotlib.use("Agg")          # write files, never open a window
import matplotlib.pyplot as plt

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# One colour per relation type, the same in every figure.
RELATION_COLOUR = {
    "finetune": SERIES[0],
    "adapter": SERIES[1],
    "quantized": SERIES[2],
    "merge": SERIES[3],
}


def apply_style():
    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelcolor": INK_SECONDARY,
        "axes.edgecolor": AXIS,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "text.color": INK,
        "lines.linewidth": 2,
        "lines.markersize": 4,
        "legend.frameon": False,
    })


def save(fig, name):
    path = f"figures/{name}.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"saved {path}")
