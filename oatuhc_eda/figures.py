"""Figures for the OAUTHC FAI validation EDA. 200 dpi, matplotlib only."""
import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

AC = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
FREQLAB = ["250", "500", "1k", "2k", "3k", "4k", "6k", "8k"]
BC = ["bc_500", "bc_1k", "bc_2k", "bc_4k"]
BCLAB = ["500", "1k", "2k", "4k"]
BC_AC = ["th_500", "th_1k", "th_2k", "th_4k"]
PTA = ["th_500", "th_1k", "th_2k", "th_4k"]
LBL6 = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
PRETTY = ["Normal", "Mild", "Moderate", "Mod. severe", "Severe", "Profound"]
CLARK = [25, 40, 55, 70, 90]

INK = "#1b1b1f"
MUTED = "#6b6b73"
GRID = "#d9d9de"
BLUE = "#2f5d8a"
TEAL = "#3d8b7d"
RUST = "#b5563f"
SAND = "#c9a227"
GREY = "#9a9aa2"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
})

df = pd.read_csv(HERE / "derived" / "analysis_with_fai.csv")
df["pta4"] = df[PTA].mean(axis=1)
df["ym"] = pd.to_datetime(df.test_year_month, errors="coerce")


def save(fig, name):
    p = FIG / name
    fig.savefig(p, dpi=200, facecolor="white")
    plt.close(fig)
    print("wrote", p.name)


# ---------- 1. age ----------
fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9), gridspec_kw={"width_ratios": [2, 1]})
ax = axes[0]
bins = np.arange(15, 105, 5)
for sx, col, lab in [(1, BLUE, "Male"), (2, RUST, "Female")]:
    ax.hist(df.loc[df.sex == sx, "age_years"], bins=bins, histtype="step", linewidth=1.5,
            color=col, label=lab)
ax.axvline(df.age_years.median(), color=INK, lw=1, ls="--")
ax.text(df.age_years.median() + 1, ax.get_ylim()[1] * 0.92, f"median {df.age_years.median():.0f}",
        fontsize=8, color=INK)
ax.set_xlabel("Age at test (years)")
ax.set_ylabel("Ears")
ax.legend(frameon=False, fontsize=8)
ax.set_title("Age distribution by sex", loc="left", fontsize=10, fontweight="bold")

ax = axes[1]
data = [df.loc[df.sex == 1, "age_years"], df.loc[df.sex == 2, "age_years"]]
bp = ax.boxplot(data, widths=0.55, patch_artist=True, medianprops=dict(color=INK, lw=1.4),
                flierprops=dict(marker="o", ms=2.5, mfc=GREY, mec="none"))
for p, c in zip(bp["boxes"], [BLUE, RUST]):
    p.set_facecolor(c); p.set_alpha(0.25); p.set_edgecolor(c)
ax.set_xticks([1, 2]); ax.set_xticklabels(["Male", "Female"])
ax.set_ylabel("Age (years)")
ax.set_title("IQR by sex", loc="left", fontsize=10, fontweight="bold")
save(fig, "fig01_age_distribution.png")

# ---------- 2. thresholds by frequency ----------
fig, ax = plt.subplots(figsize=(7.4, 3.3))
pos = np.arange(len(AC))
w = 0.36
for k, (ear, off, col) in enumerate([("left", -w / 2, BLUE), ("right", w / 2, TEAL)]):
    d = df[df.ear == ear]
    v = [d[c].dropna().values for c in AC]
    bp = ax.boxplot(v, positions=pos + off, widths=w * 0.9, patch_artist=True,
                    medianprops=dict(color=INK, lw=1.3), showfliers=False,
                    whiskerprops=dict(color=col, lw=1), capprops=dict(color=col, lw=1),
                    boxprops=dict(facecolor=col, edgecolor=col))
    for p in bp["boxes"]:
        p.set_alpha(0.22)
ax.set_xticks(pos); ax.set_xticklabels(FREQLAB)
ax.invert_yaxis()
ax.set_xlabel("Frequency (Hz, air conduction)")
ax.set_ylabel("dB HL")
ax.legend(handles=[Patch(facecolor=BLUE, alpha=.35, label="Left ear"),
                   Patch(facecolor=TEAL, alpha=.35, label="Right ear")], frameon=False, fontsize=8,
          loc="upper right", bbox_to_anchor=(1.0, 0.86))
ax.set_title("Air-conduction thresholds by frequency and ear (box = IQR, line = median)",
             loc="left", fontsize=10, fontweight="bold")
save(fig, "fig02_thresholds_by_frequency.png")

# ---------- 3. collection period ----------
per = df.dropna(subset=["ym"]).groupby(df.ym.dt.to_period("M")).size()
per.index = per.index.to_timestamp()
idx = pd.period_range("2020-01", "2026-07", freq="M").to_timestamp()
per = per.reindex(idx, fill_value=0)
fig, ax = plt.subplots(figsize=(7.4, 3.0))
ax.bar(per.index, per.values, width=24, color=BLUE, alpha=0.85)
ax.axvspan(pd.Timestamp("2023-01-01"), pd.Timestamp("2024-01-01"), color=RUST, alpha=0.10)
ax.text(pd.Timestamp("2023-04-01"), max(per.values) * 0.82, "no records\nin 2023",
        ha="center", fontsize=8, color=RUST, fontweight="bold")
ax.set_ylabel("Ears")
ax.set_xlabel("Month of testing")
ax.set_title("Records per month across the 2020–2026 study window", loc="left",
             fontsize=10, fontweight="bold")
ax.margins(x=0.01)
save(fig, "fig03_collection_timeline.png")

# ---------- 4. missingness ----------
fig, ax = plt.subplots(figsize=(7.4, 2.8))
years = sorted(df.dropna(subset=["ym"]).ym.dt.year.unique())
all_years = list(range(int(min(years)), int(max(years)) + 1))   # keep 2023 as an empty column
mat = []
for c in AC + BC:
    mat.append([100 * df.loc[df.ym.dt.year == y, c].isna().mean() if y in years else np.nan
                for y in all_years])
mat = np.ma.masked_invalid(np.array(mat))
im = ax.imshow(mat, aspect="auto", cmap="bone_r", vmin=0, vmax=100)
ax.set_xticks(range(len(all_years))); ax.set_xticklabels(all_years)
ax.set_yticks(range(len(AC + BC)))
ax.set_yticklabels([f"{f} Hz" for f in FREQLAB] + ["BC 500", "BC 1k", "BC 2k", "BC 4k"])
ax.grid(False)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        if not np.ma.is_masked(mat[i, j]) and mat[i, j] > 0:
            ax.text(j, i, f"{mat[i,j]:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if mat[i, j] > 55 else INK)
ax.text(all_years.index(2023), 5.0, "no records", ha="center", va="center", rotation=90,
        fontsize=7, color=RUST, fontweight="bold")
cb = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.03)
cb.set_label("% missing", fontsize=8)
cb.ax.tick_params(labelsize=7)
ax.set_title("Missingness by frequency and year — 3 kHz is absent from 2022 onward",
             loc="left", fontsize=10, fontweight="bold")
save(fig, "fig04_missingness_by_frequency_year.png")

# ---------- 5. PTA4 and boundaries  (the boundary-proximity figure) ----------
fig, axes = plt.subplots(2, 1, figsize=(7.4, 4.6),
                         gridspec_kw={"height_ratios": [2.2, 1]})
ax = axes[0]
for b in CLARK:
    ax.axvspan(b - 5, b + 5, color=SAND, alpha=0.16, lw=0)
for b in CLARK:
    ax.axvline(b, color=MUTED, lw=0.9, ls=":")
ax.hist(df.pta4, bins=np.arange(0, 125, 2.5), color=BLUE, alpha=0.8, edgecolor="white", lw=0.4)
ax.set_ylabel("Ears")
n_b = int((df.pta4.apply(lambda p: any(abs(p - c) <= 5 for c in CLARK))).sum())
ax.set_title(f"PTA-4 against the Clark boundaries — {n_b} of {len(df)} ears "
             f"({100*n_b/len(df):.1f}%) lie within ±5 dB of a boundary",
             loc="left", fontsize=10, fontweight="bold")
ax.legend(handles=[Patch(facecolor=SAND, alpha=.35, label="±5 dB boundary zone")],
          frameon=False, fontsize=8, loc="upper right")

ax = axes[1]
d = df.pta4.apply(lambda p: min(abs(p - c) for c in CLARK))
ax.hist(d, bins=np.arange(0, 22, 1), color=TEAL, alpha=0.85, edgecolor="white", lw=0.4)
ax.axvline(5, color=RUST, lw=1.2, ls="--")
ax.set_xlim(0, 21)
ax.text(5.5, ax.get_ylim()[1] * 0.78, "5 dB cut-off", color=RUST, fontsize=7.5)
ax.set_xlabel("Distance from nearest Clark boundary (dB)")
ax.set_ylabel("Ears")
ax.set_title(f"Distance from the nearest boundary (median {d.median():.1f} dB; "
             f"{100*(d<=2).mean():.0f}% within 2 dB)", loc="left", fontsize=9.5)
save(fig, "fig05_pta4_boundary_proximity.png")

# ---------- 6. grade distributions by scheme ----------
schemes = [
    ("Clark / protocol WHO (6)", [int((df.pta4.apply(lambda p: sum(p > c for c in CLARK)) == i).sum())
                                  for i in range(6)], PRETTY),
    ("WHO 1997 (5, per repo script)",
     [int((df.pta4.apply(lambda p: sum(p > c for c in [25, 40, 60, 80])) == i).sum()) for i in range(5)],
     ["Normal", "Mild", "Moderate", "Severe", "Profound"]),
    ("Consultant grade (6)", [int((df.consultant_grade == g).sum()) for g in LBL6], PRETTY),
]
fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.9), sharey=True)
for ax, (title, counts, labels) in zip(axes, schemes):
    ax.bar(range(len(counts)), counts, color=TEAL, alpha=0.85)
    for i, c in enumerate(counts):
        ax.text(i, c + 3, str(c), ha="center", fontsize=7.5, color=INK)
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7.5)
    ax.set_title(title, loc="left", fontsize=8.5, fontweight="bold")
    ax.set_ylim(0, max(max(s[1]) for s in schemes) * 1.16)
axes[0].set_ylabel("Ears")
save(fig, "fig06_grade_distributions.png")

# ---------- 7. air-bone gap ----------
fig, ax = plt.subplots(figsize=(7.4, 3.1))
pos = np.arange(len(BC))
for i, (bc, ac) in enumerate(zip(BC, BC_AC)):
    d = (df[bc] - df[ac]).dropna()
    vp = ax.violinplot([d.values], positions=[i], widths=0.7, showextrema=False)
    for b in vp["bodies"]:
        b.set_facecolor(BLUE); b.set_alpha(0.28); b.set_edgecolor(BLUE)
    q1, med, q3 = np.percentile(d, [25, 50, 75])
    ax.plot([i, i], [q1, q3], color=BLUE, lw=4, solid_capstyle="butt")
    ax.plot(i, med, "o", color="white", ms=4, mec=BLUE, mew=1.2)
ax.axhline(0, color=INK, lw=1)
ax.axhline(10, color=RUST, lw=1, ls="--")
ax.text(0.015, 11.2, "protocol tolerance (+10 dB)", ha="left", fontsize=7.5, color=RUST,
        transform=ax.get_yaxis_transform())
ax.set_xticks(pos); ax.set_xticklabels(BCLAB)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("BC − AC (dB)")
ax.set_title("Air–bone gap; positive values are physically implausible (BC worse than AC)",
             loc="left", fontsize=9.5, fontweight="bold")
save(fig, "fig07_air_bone_gap.png")

# ---------- 8. 120 dB HL ----------
fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9))
ax = axes[0]
c120 = [(df[c] == 120).sum() for c in AC]
c115 = [(df[c] == 115).sum() for c in AC]
x = np.arange(len(AC))
ax.bar(x - 0.2, c120, 0.4, color=RUST, alpha=0.85, label="= 120")
ax.bar(x + 0.2, c115, 0.4, color=SAND, alpha=0.9, label="= 115")
ax.set_xticks(x); ax.set_xticklabels(FREQLAB)
ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("Cells")
ax.set_title("Count of 120 and 115 dB HL", loc="left", fontsize=9.5, fontweight="bold")
ax.legend(frameon=False, fontsize=7.5)

ax = axes[1]
n = (df[AC] == 120).sum(axis=1)
vc = n.value_counts().sort_index()
ax.bar(vc.index, vc.values, color=BLUE, alpha=0.85)
ax.set_xlabel("Number of frequencies at 120 dB HL in the ear")
ax.set_ylabel("Ears")
ax.set_title(f"{(n>0).sum()} ears carry at least one 120", loc="left", fontsize=9.5,
             fontweight="bold")
save(fig, "fig08_120_pattern.png")

# ---------- 9. FAI agreement ----------
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.3), gridspec_kw={"width_ratios": [1, 1.15]})
ax = axes[0]
sub = df[df.fai_label.isin(LBL6)]
ct = pd.crosstab(sub.who_clark, sub.fai_label).reindex(index=LBL6, columns=LBL6).fillna(0)
im = ax.imshow(ct.values, cmap="Blues")
ax.set_xticks(range(6)); ax.set_xticklabels(PRETTY, rotation=45, ha="right", fontsize=7)
ax.set_yticks(range(6)); ax.set_yticklabels(PRETTY, fontsize=7)
ax.set_xlabel("FAI label"); ax.set_ylabel("Clark grade (PTA-4)")
ax.grid(False)
vmax = ct.values.max()
for i in range(6):
    for j in range(6):
        v = int(ct.values[i, j])
        if v:
            ax.text(j, i, v, ha="center", va="center", fontsize=7,
                    color="white" if v > vmax * 0.55 else INK)
ax.set_title(f"FAI vs Clark (n={len(sub)})", loc="left", fontsize=9.5, fontweight="bold")

ax = axes[1]
ok = df.fai_score.notna()
ax.scatter(df.loc[ok, "pta4"], df.loc[ok, "fai_score"], s=9, color=BLUE, alpha=0.55, lw=0)
lim = [0, 125]
ax.plot(lim, lim, color=MUTED, lw=1, ls=":")
for b in CLARK:
    ax.axvline(b, color=GRID, lw=0.8, zorder=0)
ax.set_xlim(0, 125); ax.set_ylim(0, 100)
ax.set_xlabel("PTA-4 (dB HL)"); ax.set_ylabel("FAI score")
ax.set_title(f"FAI score vs PTA-4 (ρ={df.fai_score.corr(df.pta4, method='spearman'):.3f})",
             loc="left", fontsize=9.5, fontweight="bold")
save(fig, "fig09_fai_agreement.png")

# ---------- 10. kappa precision ----------
kp = json.loads((HERE / "stage2.json").read_text())["kappa_precision"]
fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.0))
fig.subplots_adjust(wspace=0.42)
ax = axes[0]
ks = [0.6, 0.7, 0.8, 0.9]
w = [kp[str(k)]["width"] for k in ks]
ax.plot(ks, w, "o-", color=BLUE, lw=1.6, ms=5)
for k, ww in zip(ks, w):
    ax.annotate(f"{ww:.3f}", (k, ww), textcoords="offset points", xytext=(0, 7),
                ha="center", fontsize=7.5)
ax.set_xlabel("True quadratic-weighted kappa")
ax.set_ylabel("Expected 95% CI width")
ax.set_title("Precision at n = 410 ears", loc="left", fontsize=9.5, fontweight="bold")
ax.set_ylim(0, max(w) * 1.25)

ax = axes[1]
ns = [int(k) for k in kp["n_vs_width"]]
ws = [kp["n_vs_width"][k] for k in kp["n_vs_width"]]
ax.plot(ns, ws, "o-", color=TEAL, lw=1.6, ms=5)
ax.axvline(410, color=RUST, lw=1, ls="--")
ax.text(410, max(ws) * 0.80, " this study", fontsize=7.5, color=RUST, ha="left")
ax.set_xscale("log")
ax.set_xticks(ns); ax.set_xticklabels([str(n) for n in ns])
ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
ax.set_xlim(170, 1900)
ax.set_xlabel("Ears analysed")
ax.set_ylabel("95% CI width (kappa = 0.8)")
ax.set_title("Precision vs sample size", loc="left", fontsize=9.5, fontweight="bold")
save(fig, "fig10_kappa_precision.png")

print("done")
