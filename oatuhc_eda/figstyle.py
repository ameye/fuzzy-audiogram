"""Shared figure style for the OAUTHC EDA.

Colours are chosen to survive greyscale printing and the palette is never the
only cue: every series also carries a distinct marker, line style or hatch.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK = "#1b1b1f"
MUTED = "#6b6b73"
GRID = "#d9d9de"
BLUE = "#2f5d8a"
TEAL = "#3d8b7d"
ORANGE = "#c0703a"
SAND = "#c9a227"
GREY = "#9a9aa2"

MARKERS = ["o", "s", "^", "D", "v", "P"]
LINESTYLES = ["-", "--", ":", "-.", (0, (5, 1, 1, 1)), (0, (3, 1, 3, 1, 3, 1))]
HATCHES = ["", "//", "\\\\", "..", "xx", "--"]

PALETTE = {
    "normal": "#cfe0ee",
    "mild": "#a8c6de",
    "moderate": "#7ea6c6",
    "moderately_severe": "#5f88ab",
    "severe": "#40678c",
    "profound": "#2f5d8a",
}

BASE_RC = {
    "font.family": "DejaVu Sans", "font.size": 8.5,
    "axes.titlesize": 9.5, "axes.labelsize": 8.5,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelsize": 7.8, "ytick.labelsize": 7.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
    "legend.frameon": False, "legend.fontsize": 7.6,
    "lines.linewidth": 1.4, "lines.markersize": 4,
}


def apply():
    plt.rcParams.update(BASE_RC)


def title(ax, text, sub=None):
    """Panel title with an optional statistic line beneath it, above the axes."""
    n = 0 if not sub else sub.count("\n") + 1
    ax.set_title(text, loc="left", fontsize=9.5, fontweight="bold", color=INK,
                 pad=6 if not sub else 11 + 8.6 * n)
    if sub:
        ax.text(0, 1.012, sub, transform=ax.transAxes, fontsize=7.3, color=MUTED,
                ha="left", va="bottom", linespacing=1.35)


def stat_note(ax, text, y=-0.30, fs=7.2):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=fs, color=MUTED,
            ha="left", va="top", wrap=True)
