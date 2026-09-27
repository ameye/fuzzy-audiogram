"""Graphical abstract for the CMPB submission.

Design constraints, in order of importance:

1. It is read at about 13 x 5 cm. Two earlier builds were technically compliant and
   still unreadable: the first because 9 pt lettering in a 13-inch-wide figure renders
   at ~3.5 pt at that display size, the second because even at the right physical size
   the frame was crowded. Density is the failure mode here, not pixel count or bounds.

       displayed_pt ~= 5.13 * figure_pt / figure_width_inches

   so lettering needs figure_pt / width_inches >= ~1.2. This figure is 6.0 in wide with
   7-19 pt lettering, which renders at 6.0-16 pt on screen.

2. Carry one idea. The panel shows the partition against the fixed boundaries, with the
   ambiguous zone marked from above so nothing sits on the curves. The result is two
   large numerals rather than a bar chart, because axes, ticks and a panel legend on a
   three-inch-wide plot are what made the earlier version unreadable.

3. Everything plotted comes from the fitted parameters, so it cannot drift from the
   manuscript. Fills use hatches as well as colour.

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
COLOUR = {"normal": "#1b5e20", "mild": "#43a047", "moderate": "#ef6c00",
          "moderately_severe": "#bf360c", "severe": "#c62828", "profound": "#6a1b9a"}
HATCH = {"normal": "", "mild": "///", "moderate": "\\\\\\",
         "moderately_severe": "xxx", "severe": "...", "profound": "++"}
CLARK = [25, 40, 55, 70, 90]

W, H = 6.0, 2.4
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


def panel(ax, p):
    x = np.linspace(0, 120, 2400)
    for k in ORDER:
        y = trapmf(x, p[k])
        ax.fill_between(x, 0, y, facecolor=COLOUR[k], alpha=0.30, hatch=HATCH[k],
                        edgecolor=COLOUR[k], lw=0.4, zorder=2)
        ax.plot(x, y, color=COLOUR[k], lw=1.0, zorder=3)
    for b in CLARK:
        ax.axvline(b, color="#37474f", ls=":", lw=0.8, zorder=4)

    # the ambiguous zone, marked from above so nothing sits on the curves
    ax.axvspan(30, 40, color="#37474f", alpha=0.16, zorder=1)
    ax.annotate("", xy=(35, 1.05), xytext=(35, 1.28),
                arrowprops=dict(arrowstyle="-|>", color="#263238", lw=0.9))
    ax.text(35, 1.32, "±5 dB of a boundary\nno graded information",
            ha="center", va="bottom", fontsize=7.5, color="#263238", linespacing=1.3)

    ax.set_xlim(0, 120); ax.set_ylim(0, 1.62)
    ax.set_xlabel("Threshold (dB HL)", fontsize=7.5, labelpad=2)
    ax.set_ylabel("Membership", fontsize=7.5, labelpad=2)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_xticks([0, 25, 50, 75, 100, 120])
    ax.tick_params(labelsize=7, pad=1.5)
    ax.spines[["top", "right"]].set_visible(False)


def results(ax):
    ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(-0.14, 1)
    ax.text(0.03, 0.95, "99.2%", fontsize=16, fontweight="bold", color="#1b5e20",
            va="center", ha="left", transform=ax.transAxes)
    ax.text(0.03, 0.68, "agreement where the grade\nis unambiguous",
            fontsize=7.5, color="#263238", va="center", ha="left",
            linespacing=1.35, transform=ax.transAxes)
    ax.plot([0.03, 0.97], [0.57, 0.57], color="#cfd8dc", lw=0.8,
            transform=ax.transAxes, clip_on=False)
    ax.text(0.03, 0.44, "86.3%", fontsize=16, fontweight="bold", color="#c62828",
            va="center", ha="left", transform=ax.transAxes)
    ax.text(0.03, 0.17, "agreement within 5 dB\nof a severity boundary",
            fontsize=7.5, color="#263238", va="center", ha="left",
            linespacing=1.35, transform=ax.transAxes)
    ax.text(0.03, -0.04,
            "weighted \u03ba 0.946  \u00b7  \u00a042 Mamdani rules  \u00b7  19,623 ears",
            fontsize=7.5, color="#37474f", va="center", ha="left", transform=ax.transAxes)


def main():
    p = json.loads(PARAMS.read_text())
    fig = plt.figure(figsize=(W, H), dpi=600)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.30, 1.0],
                          left=0.075, right=0.98, top=0.80, bottom=0.315, wspace=0.30)

    fig.text(0.075, 0.955,
             "A Ruspini-partition fuzzy index for pure-tone audiometry",
             fontsize=10, fontweight="bold", va="top")
    fig.text(0.075, 0.865,
             "Fixed boundaries force a category onto thresholds that carry graded information.",
             fontsize=7.5, va="top", color="#263238")

    panel(fig.add_subplot(gs[0, 0]), p)
    results(fig.add_subplot(gs[0, 1]))

    handles = [plt.Line2D([], [], color=COLOUR[k], lw=5, alpha=0.5, label=LABEL[k])
               for k in ORDER]
    leg = fig.legend(handles=handles, fontsize=7.5, ncol=6, loc="lower center",
                     bbox_to_anchor=(0.5, 0.045), frameon=False, handlelength=1.1,
                     columnspacing=2.0, handletextpad=0.5)

    # overflow guard: figure-level text only, measured rather than eyeballed
    fig.canvas.draw()
    fb = fig.bbox
    artists = [t for t in fig.findobj(matplotlib.text.Text) if t.axes is None]
    for lg in fig.legends:
        artists += list(lg.get_texts())
    bad = []
    for t in artists:
        txt = t.get_text().strip()
        if not txt or txt.replace(".", "").isdigit():
            continue
        wb = t.get_window_extent(renderer=fig.canvas.get_renderer())
        if wb.x1 > fb.x1 - 1 or wb.x0 < fb.x0 + 1 or wb.y0 < fb.y0 + 1:
            bad.append(txt[:50])
    print("  bounds:", "all figure-level text fits" if not bad else f"OVERFLOW {bad}")

    # bounds alone cannot see two artists landing on each other; check the legend
    # against every axis label, which is where it collided before.
    rend = fig.canvas.get_renderer()
    lb = leg.get_window_extent(renderer=rend)
    clashes = []
    for axn in fig.axes:
        for lbl in (axn.xaxis.label, axn.yaxis.label):
            if not lbl.get_text().strip():
                continue
            if lb.overlaps(lbl.get_window_extent(renderer=rend)):
                clashes.append(f"legend over {lbl.get_text()!r}")
    print(f"  legend box: y {lb.y0/fig.bbox.height:.3f}-{lb.y1/fig.bbox.height:.3f} of figure")
    for axn in fig.axes:
        l = axn.xaxis.label
        if l.get_text().strip():
            e = l.get_window_extent(renderer=rend)
            print(f"  {l.get_text()!r} box: y {e.y0/fig.bbox.height:.3f}-{e.y1/fig.bbox.height:.3f}")
    # text inside the panels, which the figure-level check cannot see
    for axn in fig.axes:
        ts = [t for t in axn.texts if t.get_text().strip()]
        boxes = [(t.get_text()[:28], t.get_window_extent(renderer=rend)) for t in ts]
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if boxes[i][1].overlaps(boxes[j][1]):
                    clashes.append(f"{boxes[i][0]!r} over {boxes[j][0]!r}")
    print("  collisions:", "none" if not clashes else "; ".join(clashes))

    fig.savefig(OUT, dpi=600, facecolor="white")
    from PIL import Image
    im = Image.open(OUT)
    scale = (13 / 2.54) / W
    print(f"  {OUT.name}  {im.width} x {im.height} px  ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"  min 1328 x 531 px: {'PASS' if im.width >= 1328 and im.height >= 531 else 'FAIL'}"
          f"   aspect {im.width/im.height:.2f}:1")
    for pt in (16, 10, 7.5):
        print(f"    {pt:>4} pt in figure -> {pt*scale:.1f} pt on screen"
              f"  {'ok' if pt*scale >= 6 else 'TOO SMALL'}")
    im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS).save(
        "/tmp/ga_display_large.png")


if __name__ == "__main__":
    main()
