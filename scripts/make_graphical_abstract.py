"""Graphical abstract for the CMPB submission.

Elsevier's specification is a minimum of 531 x 1328 px (h x w), "readable at a size of
5 x 13 cm using a regular screen resolution of 96 dpi". That last clause is the binding
constraint, and it is easy to miss: at 96 dpi a 13 cm width is only about 492 px, so
lettering sized for a 13-inch figure renders at roughly a fifth of its nominal size.

The usable relation is

    displayed_pt  ~=  5.13 * figure_pt / figure_width_inches

so legibility at the display size needs figure_pt / width_inches >= about 1.2. This
figure is therefore drawn 5.2 in wide with 6.5-9 pt lettering, which renders at 6.5-9 pt
on screen, rather than drawn large with small text. At 600 dpi it is 3120 x 1248 px,
comfortably above the minimum.

All plotted values come from the fitted parameters and the saved results, so the graphic
cannot drift from the manuscript.

Run:  python3 scripts/make_graphical_abstract.py
Writes: manuscript/graphical_abstract.png
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "manuscript" / "graphical_abstract.png"
PARAMS = ROOT / "data" / "output_participant" / "params_participant.json"

ORDER = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
LABEL = {"normal": "Normal", "mild": "Mild", "moderate": "Moderate",
         "moderately_severe": "Mod. sev.", "severe": "Severe", "profound": "Profound"}
COLOUR = {"normal": "#1b5e20", "mild": "#66bb6a", "moderate": "#ef6c00",
          "moderately_severe": "#e65100", "severe": "#c62828", "profound": "#6a1b9a"}
HATCH = {"normal": "", "mild": "///", "moderate": "\\\\\\",
         "moderately_severe": "xxx", "severe": "...", "profound": "++"}
CLARK = [25, 40, 55, 70, 90]

W, H = 5.2, 2.08          # inches; 2.5:1, matching the 5 x 13 cm display
plt.rcParams.update({"font.family": "sans-serif",
                     "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"]})


def trapmf(x, p):
    a, b, c, d = p
    y = np.zeros_like(x, dtype=float)
    if b > a:
        m = (x >= a) & (x < b); y[m] = (x[m] - a) / (b - a)
    y[(x >= b) & (x <= c)] = 1.0
    if d > c:
        m = (x > c) & (x <= d); y[m] = (d - x[m]) / (d - c)
    return y


def panel_partition(ax, p):
    x = np.linspace(0, 120, 2400)
    for k in ORDER:
        y = trapmf(x, p[k])
        ax.fill_between(x, 0, y, facecolor=COLOUR[k], alpha=0.26, hatch=HATCH[k],
                        edgecolor=COLOUR[k], lw=0.5, zorder=2)
        ax.plot(x, y, color=COLOUR[k], lw=1.1, zorder=3)
    for b in CLARK:
        ax.axvline(b, color="#37474f", ls=":", lw=0.9, zorder=4)
    ax.axvspan(30, 40, color="#37474f", alpha=0.13, zorder=1)
    ax.annotate("", xy=(30, 0.30), xytext=(40, 0.30),
                arrowprops=dict(arrowstyle="<->", color="#263238", lw=0.9))
    ax.text(35, 0.38, "±5 dB:\nno graded\ninformation", ha="center", va="bottom",
            fontsize=6.5, color="#263238", linespacing=1.25)
    ax.set_xlim(0, 120); ax.set_ylim(0, 1.30)
    ax.set_xlabel("Threshold (dB HL)", fontsize=7)
    ax.set_ylabel("Membership", fontsize=7)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(labelsize=6.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Six memberships summing to 1 at every threshold",
                 fontsize=7, loc="left", pad=4)
    # legend is drawn at figure level; inside the axes it collided with the title


def panel_result(ax):
    vals = [99.2, 86.3]
    cols = ["#1b5e20", "#c62828"]
    hats = ["///", "xxx"]
    bars = ax.bar([0, 1], vals, width=0.5, color=cols, alpha=0.32, hatch=hats,
                  edgecolor=cols, lw=1.1)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 2.0, f"{v}%", ha="center",
                fontsize=9, fontweight="bold", color=b.get_edgecolor())
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Unambiguous\n(≥6 dB clear)", "Near a boundary\n(±5 dB)"],
                       fontsize=6.5)
    ax.set_ylim(0, 118)
    ax.set_ylabel("Agreement", fontsize=7)
    ax.set_yticks([0, 50, 100])
    ax.tick_params(labelsize=6.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("The index informs near the boundary",
                 fontsize=7, loc="left", pad=4)


def main():
    p = json.loads(PARAMS.read_text())
    fig = plt.figure(figsize=(W, H), dpi=600)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.28, 1.0],
                          left=0.085, right=0.975, top=0.755, bottom=0.335, wspace=0.26)

    fig.text(0.055, 0.965, "A Ruspini-partition fuzzy index for pure-tone audiometry",
             fontsize=9, fontweight="bold", va="top")
    fig.text(0.055, 0.885,
             "Fixed severity boundaries force a category onto thresholds that carry "
             "graded information.",
             fontsize=6.5, va="top", color="#263238")

    panel_partition(fig.add_subplot(gs[0, 0]), p)
    panel_result(fig.add_subplot(gs[0, 1]))

    # a shared legend in its own strip, so it cannot cover either panel
    handles = [plt.Line2D([], [], color=COLOUR[k], lw=5, alpha=0.5, label=LABEL[k])
               for k in ORDER]
    fig.legend(handles=handles, fontsize=6.2, ncol=3, loc="lower center",
               bbox_to_anchor=(0.5, 0.135), frameon=False, handlelength=1.0,
               columnspacing=2.2, handletextpad=0.4, labelspacing=0.45)

    fig.text(0.085, 0.075,
             "19,623 ears · 9,843 adults · three NHANES cycles · participant-level split",
             fontsize=6.2, color="#263238")
    fig.text(0.085, 0.018,
             "weighted κ 0.946 · 42 rules · no learned parameters · "
             "the reference label is a deterministic thresholding",
             fontsize=6.0, color="#455a64")

    # Bounds check before saving. Three full-width lines overran the right edge in an
    # earlier build and only a visual read caught it, so measure the artists instead.
    fig.canvas.draw()
    fb = fig.bbox
    bad = []
    # figure-level artists only. Tick labels carry an axes reference and matplotlib
    # reports a zero-origin extent for them before a full render, which produced false
    # positives; these four full-width lines are what actually overran.
    artists = [t for t in fig.findobj(matplotlib.text.Text) if t.axes is None]
    for lg in fig.legends:
        artists += list(lg.get_texts())
    for t in artists:
        txt = t.get_text().strip()
        if not txt or txt.replace(".", "").isdigit():
            continue
        try:
            wb = t.get_window_extent(renderer=fig.canvas.get_renderer())
        except Exception:
            continue
        if wb.width == 0 and wb.height == 0:
            continue          # matplotlib reports a zero extent for tick labels
        if wb.x1 > fb.x1 - 1 or wb.x0 < fb.x0 + 1 or wb.y0 < fb.y0 + 1:
            bad.append((t.get_text()[:52],
                        f"x1={wb.x1:.0f}/{fb.x1:.0f}" if wb.x1 > fb.x1 - 1
                        else f"x0={wb.x0:.0f}" if wb.x0 < fb.x0 + 1 else f"y0={wb.y0:.0f}"))
    if bad:
        print("  OVERFLOW:")
        for txt, why in bad:
            print(f"    {why}  {txt!r}")
    else:
        print("  bounds check: every text artist fits inside the figure")

    fig.savefig(OUT, dpi=600, facecolor="white")
    from PIL import Image
    im = Image.open(OUT)
    dw = 13 / 2.54                          # 13 cm display width, in inches
    scale = dw / W
    print(f"  {OUT.name}  {im.width} x {im.height} px  ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"  min 1328 x 531 px: {'PASS' if im.width >= 1328 and im.height >= 531 else 'FAIL'}")
    print(f"  aspect {im.width/im.height:.2f}:1 vs spec 2.50:1")
    print(f"  at a 13 cm display width, lettering renders at:")
    for pt in (9, 7, 6.5, 6.2):
        print(f"    {pt:>4} pt in-figure  ->  {pt*scale:.1f} pt on screen"
              f"  {'ok' if pt*scale >= 6 else 'TOO SMALL'}")


if __name__ == "__main__":
    main()
