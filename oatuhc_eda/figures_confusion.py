"""Confusion matrices for the two WHO reference schemes. 200 dpi, one figure."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

HERE = Path("/workspace/fuzzy-audiogram/oatuhc_eda")
FIG = HERE / "figures"
INK, MUTED = "#1b1b1f", "#6b6b73"
BLUE = "#2f5d8a"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
})

data = json.loads((HERE / "stage5.json").read_text())
cmap = LinearSegmentedColormap.from_list("fai", ["#ffffff", "#c9d8e6", BLUE])

panels = [
    ("fai_vs_protocol_who",
     "A. Protocol WHO reference, six grades (25/40/55/70/90 dB)",
     "protocol-who-6"),
    ("fai_vs_script_who",
     "B. Shipped `validate_oatuhc.py` reference, five grades (25/40/60/80 dB)",
     "script-who-5"),
]

texts = []
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3),
                         gridspec_kw={"width_ratios": [6, 5]})

for ax, (key, title, slug) in zip(axes, panels):
    block = data[key]
    labels = block["crosstab_reference_rows"]["labels"]
    matrix = np.array(block["crosstab_reference_rows"]["matrix"], dtype=float)
    k = len(labels)
    row_tot = matrix.sum(1, keepdims=True)
    share = np.divide(matrix, row_tot, out=np.zeros_like(matrix), where=row_tot > 0)

    ax.imshow(share, cmap=cmap, vmin=0, vmax=1, aspect="equal")
    for i in range(k):
        for j in range(k):
            n = int(matrix[i, j])
            if n == 0:
                ax.text(j, i, "·", ha="center", va="center", color="#c2c2c8", fontsize=9)
                continue
            share_txt = f"{100 * share[i, j]:.0f}%"
            colour = "white" if share[i, j] > 0.55 else INK
            ax.text(j, i - 0.08, f"{n}", ha="center", va="center",
                    color=colour, fontsize=9, fontweight="bold" if i == j else "normal")
            ax.text(j, i + 0.24, share_txt, ha="center", va="center",
                    color=colour, fontsize=7)
    ax.set_xticks(range(k), labels, rotation=35, ha="right")
    ax.set_yticks(range(k), labels)
    ax.set_xlabel("")
    label_text = ax.text(0.5, -0.26, "FAI grade", transform=ax.transAxes,
                         ha="center", va="top", fontsize=8.5, color=INK)
    ax.set_ylabel("Reference grade")
    ax.set_title(title, loc="left", fontsize=9.5, fontweight="bold", pad=8)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    note = f"n = {block['n']}   exact {100 * block['exact']:.1f}%   "
    note += (f"κquad {block['kappa_quadratic']:.3f}   "
             f"κunw {block['kappa_unweighted']:.3f}")
    if key == "fai_vs_script_who":
        note += "\n66 FAI moderately-severe ears have no five-grade counterpart and are excluded"
    note_text = ax.text(0.5, -0.36, note,
                        transform=ax.transAxes, ha="center", va="top",
                        fontsize=7.4, color=MUTED)
    texts.append((label_text, note_text, ax))

fig.suptitle("FAI against WHO PTA-4 grades, OAUTHC validation (410 ears), after the unfired-consequent fix",
             x=0.02, ha="left", fontsize=10.5, fontweight="bold")
fig.text(0.02, -0.02,
         "Cell = ears; upper figure is the row percentage. Rows sum to the reference grade count, columns to the FAI grade count.",
         fontsize=7.4, color=MUTED, ha="left")
fig.tight_layout()
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
for label_text, note_text, ax in texts:
    a = label_text.get_window_extent(renderer)
    b = note_text.get_window_extent(renderer)
    overlap = not (b.y1 <= a.y0 or b.y0 >= a.y1 or b.x1 <= a.x0 or b.x0 >= a.x1)
    print(f"label y [{a.y0:.0f},{a.y1:.0f}]  note y [{b.y0:.0f},{b.y1:.0f}]  overlap={overlap}")
    ax_bottom = ax.get_window_extent(renderer).y0
    print(f"   axes bottom {ax_bottom:.0f}; lowest text {min(a.y0, b.y0):.0f}")

out = FIG / "fig11_confusion_matrices.png"
fig.savefig(out, dpi=200, facecolor="white")
print("wrote", out)
