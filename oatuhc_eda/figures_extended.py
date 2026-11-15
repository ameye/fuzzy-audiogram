"""Extended figures 11-35 for the OAUTHC FAI validation EDA.

Every panel carries the statistic that justifies it (n, median/IQR, the test
and its p-value, effect size) so the figure and the report table cannot drift.
200 dpi, sized for A4 width (7.2 in), no colour-only encodings.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import gaussian_kde

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402
import matplotlib.ticker  # noqa: E402

import figstyle as F  # noqa: E402

F.apply()
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
J = json.loads((HERE / "descriptive.json").read_text())

AC = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
FREQ = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
FREQLAB = ["250", "500", "1k", "2k", "3k", "4k", "6k", "8k"]
BC = ["bc_500", "bc_1k", "bc_2k", "bc_4k"]
BC_AC = ["th_500", "th_1k", "th_2k", "th_4k"]
BCLAB = ["500", "1k", "2k", "4k"]
PTA4 = ["th_500", "th_1k", "th_2k", "th_4k"]
LBL6 = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
PRETTY = ["Normal", "Mild", "Moderate", "Mod. severe", "Severe", "Profound"]
PRETTY_SHORT = ["Normal", "Mild", "Moderate", "Mod-sev", "Severe", "Profound"]
DIAG_ORDER = ["presbyacusis", "meniere", "ototoxicity", "otosclerosis", "csom", "nihl",
              "ssnhl", "other", "not_documented"]
DIAG_PRETTY = {"presbyacusis": "Presbyacusis", "meniere": "Meniere", "ototoxicity": "Ototoxicity",
               "otosclerosis": "Otosclerosis", "csom": "CSOM", "nihl": "NIHL",
               "ssnhl": "SSNHL", "other": "Other", "not_documented": "Not documented"}
CLARK = [25, 40, 55, 70, 90]

df = pd.read_csv(HERE / "derived" / "analysis_with_fai.csv")
df["pta4"] = df[PTA4].mean(axis=1)
df["pta3"] = df[["th_500", "th_1k", "th_2k"]].mean(axis=1)
df["pta8"] = df[AC].mean(axis=1)
df["ok"] = df.fai_score.notna()
df["year"] = pd.to_datetime(df.test_year_month, errors="coerce").dt.year
df["ym"] = pd.to_datetime(df.test_year_month, errors="coerce")
df = df.merge(pd.read_csv(HERE / "derived" / "clusters.csv"), on="study_id", how="left")
_ABG = np.asarray(df[BC].values, float) - np.asarray(df[BC_AC].values, float)
df["abg_mean"] = np.nanmean(_ABG, axis=1)


def _text_overlaps(fig):
    """Flag Text artists whose bounding boxes collide (a layout defect)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    ticks = set()
    for ax in fig.get_axes():
        for t in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            ticks.add(id(t))
    items = []
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_visible() or not t.get_text().strip():
            continue
        try:
            bb = t.get_window_extent(r)
        except Exception:
            continue
        if bb.width <= 1 or bb.height <= 1:
            continue
        items.append((t.get_text().replace("\n", " / ")[:42], bb, id(t) in ticks))
    bad = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i][2] and items[j][2]:
                continue                      # adjacent tick labels are laid out by matplotlib
            a, b = items[i][1], items[j][1]
            ov = matplotlib.transforms.Bbox.intersection(a, b)
            if ov is None:
                continue
            area = ov.width * ov.height
            if area > 0.25 * min(a.width * a.height, b.width * b.height):
                bad.append((items[i][0], items[j][0]))
    return bad


def save(fig, name):
    p = FIG / name
    bad = _text_overlaps(fig)
    if bad:
        print(f"  !! {name}: {len(bad)} text collisions")
        for a, b in bad[:4]:
            print(f"     '{a}' <> '{b}'")
    fig.savefig(p, dpi=200, facecolor="white")
    plt.close(fig)
    print("wrote", p.name)


def pfmt(p):
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}"


def box(ax, groups, labels, colors, widths=0.5, showfliers=False, positions=None,
        markers=None, alphas=0.3):
    positions = np.arange(len(groups)) if positions is None else positions
    bp = ax.boxplot(groups, positions=positions, widths=widths, patch_artist=True,
                    showfliers=showfliers, medianprops=dict(color=F.INK, lw=1.4),
                    whiskerprops=dict(color=F.MUTED, lw=1),
                    capprops=dict(color=F.MUTED, lw=1),
                    flierprops=dict(marker="o", ms=2.2, mfc=F.GREY, mec="none", alpha=0.5))
    for p, c in zip(bp["boxes"], colors):
        p.set_facecolor(c); p.set_alpha(alphas); p.set_edgecolor(c); p.set_linewidth(1.1)
    ax.set_xticks(positions); ax.set_xticklabels(labels)
    return bp


# ============================================================== 11. age by ear and sex
a = J["age"]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.05, 1]})
ax = axes[0]
pos, groups, labels, cols, mks = [], [], [], [], []
for i, (sx, sxlab) in enumerate([(1, "Male"), (2, "Female")]):
    for j, ear in enumerate(["left", "right"]):
        v = df.loc[(df.sex == sx) & (df.ear == ear), "age_years"]
        groups.append(v.values)
        pos.append(i * 2.6 + j)
        labels.append(f"{sxlab[0]}\n{ear[0].upper()}")
        cols.append(F.BLUE if sx == 1 else F.ORANGE)
        mks.append(F.MARKERS[j])
box(ax, groups, labels, cols, positions=pos, widths=0.62, showfliers=True)
rng = np.random.default_rng(2)
for p, v, mk, c in zip(pos, groups, mks, cols):
    ax.plot(p + rng.normal(0, 0.05, len(v)), v, mk, ms=1.8, color=c, alpha=0.32, mec="none")
    ax.text(p, 103, f"n={len(v)}", ha="center", fontsize=6.6, color=F.MUTED)
ax.set_ylabel("Age at test (years)")
ax.set_ylim(10, 108)
ax.set_xlabel("Male (M) / Female (F), left (L) / right (R) ear")
F.title(ax, "Age by sex and ear", "box = IQR, whiskers = 1.5 x IQR, points = ears")
note11 = (f"sex: U={a['test_sex']['U']:.0f}, {pfmt(a['test_sex']['p'])}, "
          f"r$_{{rb}}$={a['test_sex']['rank_biserial']:+.03f}\near: U={a['test_ear']['U']:.0f}, "
          f"{pfmt(a['test_ear']['p'])}")

ax = axes[1]
for sx, lab, c, ls, mk in [(1, "Male", F.BLUE, "-", "o"), (2, "Female", F.ORANGE, "--", "s")]:
    v = np.sort(df.loc[df.sex == sx, "age_years"].values)
    ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", color=c, ls=ls, label=lab)
    ax.plot(np.median(v), 0.5, mk, color=c, ms=5, mec="white", mew=0.8, zorder=5)
ax.axhline(0.5, color=F.GREY, lw=0.8, ls=":")
ax.set_xlabel("Age at test (years)")
ax.set_ylabel("Cumulative proportion of ears")
ax.legend(loc="lower right")
F.title(ax, "Age distribution, cumulative", "markers: group medians (61 vs 59 years)")
ax.set_xlim(15, 100)
fig.subplots_adjust(bottom=0.30, top=0.86)
fig.text(0.012, 0.02, note11, fontsize=6.8, color=F.MUTED, ha="left", va="bottom")
save(fig, "fig11_age_by_ear_sex.png")

# ============================================================== 12. age by grade
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
for ax, (key, lab) in zip(axes, [("by_grade_clark", "Clark / protocol WHO grade"),
                                 ("by_grade_consult", "Consultant grade")]):
    d = a[key]
    groups = [df.loc[df.consultant_grade == g, "age_years"].values if key == "by_grade_consult"
              else df.loc[df.who_clark == g, "age_years"].values for g in LBL6]
    box(ax, groups, PRETTY_SHORT, [F.PALETTE[g] for g in LBL6], widths=0.6, showfliers=True)
    for lb in ax.get_xticklabels():
        lb.set_rotation(30); lb.set_ha("right")
    for i, (g, v) in enumerate(zip(LBL6, groups)):
        ax.text(i, 102, f"n={len(v)}", ha="center", fontsize=6.4, color=F.MUTED)
        ax.text(i, 98.5, f"{np.median(v):.0f}", ha="center", fontsize=6.8, color=F.INK,
                fontweight="bold")
    t = a["test_grade_clark"] if key == "by_grade_clark" else a["test_grade_consult"]
    ax.text(0.02, 0.03, f"Kruskal-Wallis H({t['df']})={t['H']:.1f}, {pfmt(t['p'])}\n"
            f"$\\epsilon^2$={t['epsilon_squared']:.2f}", transform=ax.transAxes,
            fontsize=6.9, color=F.INK, bbox=dict(facecolor="white", edgecolor=F.GRID,
            boxstyle="round,pad=0.3", alpha=0.92))
    F.title(ax, lab, "bold figure = median age")
axes[0].set_ylabel("Age at test (years)")
axes[0].set_ylim(-8, 108)
fig.suptitle("Age rises with grade to 'moderately severe' and then falls: profound ears are "
             "younger\n(Spearman rho against ordered grade = "
             f"{a['trend_grade_clark']['rho']:+.2f}, {pfmt(a['trend_grade_clark']['p'])})",
             x=0.01, ha="left", fontsize=8.4, y=1.17)
save(fig, "fig12_age_by_grade.png")

# ============================================================== 13. age by diagnosis
fig, ax = plt.subplots(figsize=(7.0, 3.2))
d = a["by_diagnosis"]
order = sorted(DIAG_ORDER, key=lambda k: d[k]["median"])
groups = [df.loc[df.diagnosis_category == k, "age_years"].values for k in order]
cols = [F.ORANGE if k in ("other", "not_documented") else F.BLUE for k in order]
box(ax, groups, ["" for _ in order], cols, widths=0.55, showfliers=True)
rng = np.random.default_rng(4)
for i, (k, v) in enumerate(zip(order, groups)):
    ax.plot(i + rng.normal(0, 0.06, len(v)), v, F.MARKERS[i % len(F.MARKERS)], ms=1.8,
            color=cols[i], alpha=0.35, mec="none")
    ax.text(i, 107, f"{np.median(v):.0f}", ha="center", fontsize=7, fontweight="bold")
    ax.text(i, 102.5, f"n={len(v)}", ha="center", fontsize=6.2, color=F.MUTED)
ax.set_xticks(range(len(order)))
ax.set_xticklabels([DIAG_PRETTY[k] for k in order], rotation=30, ha="right")
ax.set_ylabel("Age at test (years)")
ax.set_ylim(10, 114)
t = a["test_diagnosis"]
ax.text(0.0, -0.30, f"Kruskal-Wallis H({t['df']})={t['H']:.1f}, {pfmt(t['p'])}, "
        f"$\\epsilon^2$={t['epsilon_squared']:.2f}; orange categories are the residual "
        "'other' and the missing bin", transform=ax.transAxes, fontsize=6.8, color=F.MUTED,
        va="top")
for p, k in zip(range(len(order)), order):
    if k in ("other", "not_documented"):
        ax.get_xticklabels()[p].set_color(F.ORANGE)
F.title(ax, "Age by aetiology category", "bold figure = median; bars ordered by median age")
save(fig, "fig13_age_by_diagnosis.png")

# ============================================================== 14. age vs PTA
fig, ax = plt.subplots(figsize=(7.2, 3.4))
ax.scatter(df.age_years, df.pta4, s=11, facecolor="none", edgecolor=F.BLUE, lw=0.7,
           alpha=0.65, marker="o", label="Ear (n=410)")
x = df.age_years.values
y = df.pta4.values
xs, ys = [], []
# bootstrap band around the local-linear smoother
rng = np.random.default_rng(9)
from statlib import lowess  # noqa: E402
xs, ys = lowess(x, y, frac=0.65, grid=80)
band = []
for _ in range(200):
    i = rng.integers(0, len(x), len(x))
    _, yb = lowess(x[i], y[i], frac=0.65, grid=80)
    band.append(yb)
band = np.array(band)
ax.fill_between(xs, np.percentile(band, 2.5, axis=0), np.percentile(band, 97.5, axis=0),
                color=F.TEAL, alpha=0.16, lw=0, label="95% bootstrap band")
ax.plot(xs, ys, color=F.TEAL, lw=2.0, ls="-", label="Local-linear smoother (span 0.65)")
o = J["age"]["age_vs_pta"]["ols"]
xx = np.linspace(17, 99, 50)
ax.plot(xx, o["intercept"] + o["slope"] * xx, color=F.ORANGE, lw=1.3, ls="--",
        label=f"OLS: +{o['slope']:.2f} dB/year")
for g, lab in [(1, "Male"), (2, "Female")]:
    pass
ax.set_xlabel("Age at test (years)")
ax.set_ylabel("PTA-4 (dB HL)")
ax.set_ylim(-34, 152)
ax.legend(loc="upper left", ncol=2, frameon=False, columnspacing=1.6,
          handletextpad=0.6)
sp = J["age"]["age_vs_pta"]
ax.text(0.985, 0.03, f"Spearman rho = {sp['spearman']:+.3f} "
        f"(95% CI {sp['spearman_ci'][0]:+.2f} to {sp['spearman_ci'][1]:+.2f})\n"
        f"OLS slope {o['slope']:+.2f} dB/year (95% CI {o['slope_ci'][0]:+.2f} to "
        f"{o['slope_ci'][1]:+.2f}), R$^2$={o['r2']:.3f}",
        transform=ax.transAxes, ha="right", fontsize=7.0, color=F.INK,
        bbox=dict(facecolor="white", edgecolor=F.GRID, boxstyle="round,pad=0.4"))
F.title(ax, "Age against PTA-4, with a fitted trend and its interval",
        "the association is positive but weak: age explains 3.5% of PTA-4 variance")
save(fig, "fig14_age_vs_pta.png")

# ============================================================== 15. sex by decade
fig, ax = plt.subplots(figsize=(7.2, 3.0))
dt = J["sex"]["decade_table"]
dec = list(dt.keys())
m = np.array([dt[k][0] for k in dec], float)
fm = np.array([dt[k][1] for k in dec], float)
tot = m + fm
ypos = np.arange(len(dec))
ax.barh(ypos, 100 * m / tot, color=F.BLUE, alpha=0.85, edgecolor="white", hatch="")
ax.barh(ypos, 100 * fm / tot, left=100 * m / tot, color=F.ORANGE, alpha=0.85,
        edgecolor="white", hatch="//")
for i in range(len(dec)):
    ax.text(2, i, f"{int(m[i])}", va="center", ha="left", fontsize=7, color="white",
            fontweight="bold")
    ax.text(97, i, f"{int(fm[i])}", va="center", ha="right", fontsize=7, color="white",
            fontweight="bold")
    ax.text(101.5, i, f"n={int(tot[i])}", va="center", fontsize=6.6, color=F.MUTED)
ax.axvline(38.5, color=F.INK, lw=1, ls=":")
ax.text(0.995, 1.012, "overall 38.5% male", fontsize=6.6, color=F.INK, ha="right",
        va="bottom", transform=ax.transAxes)
ax.set_yticks(ypos); ax.set_yticklabels(dec)
ax.set_xlim(0, 120); ax.set_xlabel("Share of ears in the decade (%)")
ax.legend(handles=[Patch(facecolor=F.BLUE, label="Male"),
                   Patch(facecolor=F.ORANGE, hatch="//", label="Female")],
          loc="upper right", ncol=2, bbox_to_anchor=(1.0, -0.20))
t = J["sex"]["decade_test"]
ax.text(0.0, -0.25, f"chi-square({t['df']})={t['chi2']:.1f}, {pfmt(t['p'])}, "
        f"Cramer's V={t['cramers_v']:.2f}", transform=ax.transAxes, fontsize=7, color=F.MUTED,
        va="top")
F.title(ax, "Sex composition by decade of age",
        "female preponderance is concentrated between 30 and 59 years")
save(fig, "fig15_sex_by_decade.png")

# ============================================================== 16. interaural asymmetry
w = df.pivot_table(index="patient_id", columns="ear", values="pta4", aggfunc="first")
diff = (w["right"] - w["left"]).dropna()
ia = J["interaural"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.1), gridspec_kw={"width_ratios": [1.15, 1]})
ax = axes[0]
bins = np.arange(-90, 95, 5)
nmax = np.histogram(diff, bins=bins)[0].max()
ax.set_ylim(0, nmax * 1.45)
ax.hist(diff, bins=bins, color=F.BLUE, alpha=0.8, edgecolor="white", lw=0.5)
for x0 in (-15, 15):
    ax.axvline(x0, color=F.ORANGE, lw=1.2, ls="--")
ax.axvline(0, color=F.INK, lw=1)
ax.text(19.0, ax.get_ylim()[1] * 0.55, "|difference|\n≥ 15 dB", color=F.ORANGE,
        fontsize=7, fontweight="bold", va="top", ha="left")
ax.set_xlabel("Right minus left PTA-4 (dB)")
ax.set_ylabel("Patients")
ax.text(0.02, 0.99, f"median {ia['median_diff']:.0f} dB, IQR {ia['q1']:.0f} to {ia['q3']:.0f}\n"
        f"{ia['n_ge15']}/{ia['n_pairs']} patients ≥15 dB ({100*ia['pct_ge15']:.1f}%)",
        transform=ax.transAxes, fontsize=6.9, color=F.INK, va="top",
        bbox=dict(facecolor="white", edgecolor=F.GRID, boxstyle="round,pad=0.3", alpha=0.95))
F.title(ax, "Interaural asymmetry", "Wilcoxon signed-rank across ears " + pfmt(ia["wilcoxon_symmetry"]["p"]))

ax = axes[1]
asym = (w["right"] - w["left"]).abs() >= 15
ax.scatter(w.loc[~asym, "left"], w.loc[~asym, "right"], s=10, marker="o", facecolor="none",
           edgecolor=F.BLUE, lw=0.7, alpha=0.7, label=f"Symmetric (<15 dB), n={int((~asym).sum())}")
ax.scatter(w.loc[asym, "left"], w.loc[asym, "right"], s=14, marker="^", facecolor=F.ORANGE,
           edgecolor="white", lw=0.4, alpha=0.9, label=f"Asymmetric (≥15 dB), n={int(asym.sum())}")
ax.plot([0, 125], [0, 125], color=F.INK, lw=1, ls=":")
ax.plot([0, 110], [15, 125], color=F.GREY, lw=0.8, ls="--")
ax.plot([15, 125], [0, 110], color=F.GREY, lw=0.8, ls="--")
ax.set_xlabel("Left PTA-4 (dB HL)")
ax.set_ylabel("Right PTA-4 (dB HL)")
ax.set_xlim(0, 125); ax.set_ylim(0, 125)
ax.legend(loc="lower right")
F.title(ax, "Left against right ear", "dotted = identity; dashed = ±15 dB")
save(fig, "fig16_interaural_asymmetry.png")

# ============================================================== 17. batch structure
per = df.dropna(subset=["ym"]).groupby(df.ym.dt.to_period("M")).size()
per.index = per.index.to_timestamp()
idx = pd.period_range("2020-01", "2026-06", freq="M").to_timestamp()
per = per.reindex(idx, fill_value=0)
fig, ax = plt.subplots(figsize=(7.4, 3.4))
ax.bar(per.index, per.values, width=24, color=F.BLUE, alpha=0.85, edgecolor="white", lw=0.3)
ax.axvspan(pd.Timestamp("2023-01-01"), pd.Timestamp("2023-12-31"), color=F.ORANGE, alpha=0.10, lw=0)
ax.text(pd.Timestamp("2023-06-15"), 8, "no records\nin 2023", ha="center", va="center",
        fontsize=7.5, color=F.ORANGE, fontweight="bold")
ax.axhline(22, color=F.MUTED, lw=0.9, ls=":")
ax.text(pd.Timestamp("2026-06-20"), 22.6, "22 / month", fontsize=6.3, color=F.MUTED,
        ha="right", va="bottom")
c = J["collection"]
for r in c["runs"]:
    a0 = pd.Timestamp(r["start"]); b0 = pd.Timestamp(r["end"])
    top = per.loc[a0:b0].max()
    ax.annotate(f"{r['ears']}", (a0 + (b0 - a0) / 2, top + 1.2), ha="center", va="bottom",
                fontsize=6.4, color=F.INK)
    ax.plot([a0, b0], [top + 0.8, top + 0.8], color=F.INK, lw=0.6, alpha=0.55)
ax.set_ylabel("Ears per month")
ax.set_xlabel("Month of testing")
ax.set_ylim(0, 36)
ax.margins(x=0.01)
fig.text(0.01, -0.04, f"{c['months_with_records']} of {c['months_in_window']} months in the window carry records "
         f"({100*c['coverage']:.0f}% coverage); {c['n_runs']} contiguous runs with sizes "
         f"{', '.join(str(r['ears']) for r in c['runs'])} ears.\n"
         f"Run sizes range {min(r['ears'] for r in c['runs'])} to {max(r['ears'] for r in c['runs'])} "
         f"(SD {c['runs_std_ears']:.0f}); 5 months sit at exactly 22 ears. This is batch extraction, "
         "not consecutive sampling.",
         fontsize=6.9, color=F.MUTED, ha="left", va="top", linespacing=1.35)
F.title(ax, "Records per month across the whole collection period",
        "figures above each bar group are the size of that contiguous extraction run")
save(fig, "fig17_batch_structure.png")

# ============================================================== 18. threshold ridgeline
fig, ax = plt.subplots(figsize=(7.2, 4.6))
grid = np.linspace(-10, 125, 300)
for i, (c, lab) in enumerate(zip(AC, FREQLAB)):
    for ear, col, ls in [("left", F.BLUE, "-"), ("right", F.ORANGE, "--")]:
        v = df.loc[df.ear == ear, c].dropna().values
        if len(v) < 10:
            continue
        kde = gaussian_kde(v, bw_method=0.28)
        dens = kde(grid)
        dens = dens / dens.max() * 0.78
        ax.fill_between(grid, i, i + dens, color=col, alpha=0.15, lw=0)
        ax.plot(grid, i + dens, color=col, ls=ls, lw=1.2)
        ax.plot(np.median(v), i + 0.04, "o" if ear == "left" else "s", color=col,
                ms=3.2, mec="white", mew=0.5, zorder=5)
    ax.text(-14, i + 0.28, lab, ha="right", va="center", fontsize=8, fontweight="bold")
    n = df[c].notna().sum()
    ml = df.loc[df.ear == "left", c].median(); mr = df.loc[df.ear == "right", c].median()
    ax.text(126, i + 0.28, f"n={n}   L {ml:.0f} / R {mr:.0f}", ha="left", va="center",
            fontsize=6.3, color=F.MUTED)
ax.set_yticks([])
ax.set_xlim(-30, 185)
ax.set_ylim(-0.3, 8.4)
ax.set_xlabel("Air-conduction threshold (dB HL); open circle = left median, square = right median")
ax.grid(axis="y", visible=False)
ax.legend(handles=[Line2D([], [], color=F.BLUE, ls="-", label="Left ear"),
                   Line2D([], [], color=F.ORANGE, ls="--", label="Right ear")],
          loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.30))
F.title(ax, "Threshold distributions at each frequency, by ear",
        "kernel density, each row scaled to its own peak; the 3 kHz row is half the sample")
save(fig, "fig18_threshold_ridgeline.png")

# ============================================================== 19. median heatmaps
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4), gridspec_kw={"width_ratios": [1, 1.35], "wspace": 0.30})
ax = axes[0]
M = np.array([[df.loc[df.ear == e, c].median() for e in ("left", "right")] for c in AC])
im = ax.imshow(M, cmap="Blues", vmin=0, vmax=120, aspect="auto")
for i in range(8):
    for j in range(2):
        ax.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=7.6,
                color="white" if M[i, j] > 70 else F.INK)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Left", "Right"], fontsize=7.6)
ax.set_yticks(range(8)); ax.set_yticklabels(FREQLAB, fontsize=7.6)
ax.set_ylabel("Frequency (Hz)")
ax.grid(False)
ax.set_title("Median threshold by ear", loc="left", fontsize=9, fontweight="bold")
ax.tick_params(axis="y", pad=2)

ax = axes[1]
M2 = np.array([[df.loc[df.consultant_grade == g, c].median() for c in AC] for g in LBL6])
im = ax.imshow(M2, cmap="Blues", vmin=0, vmax=120, aspect="auto")
for i in range(len(LBL6)):
    for j in range(8):
        ax.text(j, i, f"{M2[i,j]:.0f}", ha="center", va="center", fontsize=7,
                color="white" if M2[i, j] > 70 else F.INK)
ax.set_xticks(range(8)); ax.set_xticklabels(FREQLAB, rotation=45, ha="right")
ax.set_yticks(range(6)); ax.set_yticklabels(PRETTY, fontsize=7.4)
ax.grid(False)
cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
cb.set_label("dB HL", fontsize=7)
ax.set_title("Median threshold stratified by consultant grade", loc="left", fontsize=9,
             fontweight="bold")
ax.set_xlabel("Frequency (Hz)")
fig.suptitle("Median air-conduction threshold by frequency: no ear effect, a clear "
             "grade gradient, and a 6 kHz excess in the profound band",
             x=0.01, ha="left", fontsize=8.6, y=1.10)
save(fig, "fig19_threshold_heatmap.png")

# ============================================================== 20. frequency correlation
fig, ax = plt.subplots(figsize=(6.2, 4.9))
M = np.array(J["thresholds"]["corr"]["matrix"])
mask = np.triu(np.ones_like(M, dtype=bool), k=1)
im = ax.imshow(np.where(mask, np.nan, M), cmap="RdBu_r", vmin=-1, vmax=1)
for i in range(8):
    for j in range(8):
        if i == j:
            ax.text(j, i, "1", ha="center", va="center", fontsize=7.5, color=F.INK)
        elif i > j:
            ax.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center", fontsize=7.4,
                    color="white" if abs(M[i, j]) > 0.7 else F.INK)
ax.set_xticks(range(8)); ax.set_xticklabels(FREQLAB)
ax.set_yticks(range(8)); ax.set_yticklabels(FREQLAB)
ax.grid(False)
ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("Frequency (Hz)")
cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
cb.set_label("Spearman rho", fontsize=7.5)
ax.set_title("Spearman correlation between the eight air-conduction frequencies",
             loc="left", fontsize=8.8, fontweight="bold")
ax.text(0, 8.9, "Adjacent frequencies correlate at rho 0.90 to 0.95 and the weakest pair is 250 Hz against "
        "8 kHz (0.66).\n3 kHz, present in only 210 ears, still correlates 0.81 to 0.95 with every other "
        "frequency, so the vector carries a strong common severity factor.",
        fontsize=6.9, color=F.MUTED, ha="left", va="top")
save(fig, "fig20_freq_correlation.png")

# ============================================================== 21. configuration clusters
C = J["clusters"]
COLS7 = ["th_250", "th_500", "th_1k", "th_2k", "th_4k", "th_6k", "th_8k"]
X = df[COLS7].copy()
X = X.fillna(X.median())
centred = X.sub(X.mean(axis=1), axis=0)
fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.9), gridspec_kw={"width_ratios": [1.2, 1], "wspace": 0.62})
ax = axes[0]
order = df.sort_values(["cluster", "th_4k"]).index
Mx = centred.loc[order].values
im = ax.imshow(Mx.T, cmap="RdBu_r", vmin=-45, vmax=45, aspect="auto")
bounds = np.cumsum([C["n"][str(j)] for j in range(C["k"])])
for b in bounds[:-1]:
    ax.axvline(b - 0.5, color=F.INK, lw=1.2)
for j in range(C["k"]):
    mid = (bounds[j] - C["n"][str(j)] / 2) / len(order)
    ax.text(mid, 1.015 if j % 2 == 0 else 1.075, f"C{j+1}  n={C['n'][str(j)]}",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.0,
            fontweight="bold", color=F.INK)
ax.set_yticks(range(7)); ax.set_yticklabels(["250", "500", "1k", "2k", "4k", "6k", "8k"])
ax.set_xticks([])
ax.set_xlabel("410 ears sorted by cluster, then by 4 kHz threshold within cluster")
ax.grid(False)
cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.015)
cb.set_label("dB from ear mean", fontsize=6.5)
ax.set_title("Ear profiles, level removed", loc="left", fontsize=9, fontweight="bold", pad=46)

ax = axes[1]
xx = np.arange(7)
for j in range(C["k"]):
    p = C["profiles_centred"][str(j)]
    vals = [p[k] for k in ["250", "500", "1000", "2000", "4000", "6000", "8000"]]
    ax.plot(xx, vals, marker=F.MARKERS[j], ls=F.LINESTYLES[j], color=[F.BLUE, F.TEAL, F.ORANGE,
            F.SAND][j], label=f"C{j+1} (n={C['n'][str(j)]}, {C['slopes_db_per_octave'][str(j)]:+.1f} dB/oct)")
ax.axhline(0, color=F.GREY, lw=0.8, ls=":")
ax.set_xticks(xx); ax.set_xticklabels(["250", "500", "1k", "2k", "4k", "6k", "8k"])
ax.set_ylabel("Median threshold minus ear mean (dB)")
ax.set_xlabel("Frequency (Hz)")
ax.legend(loc="upper left")
ax.set_title("Cluster median profiles", loc="left", fontsize=9, fontweight="bold")
fig.suptitle("Configuration clustering: the data separate into a flat group and three "
             "degrees of high-frequency slope\nSilhouette at k=4 is "
             f"{C['silhouette']['4']:.2f} (best at k=2, {C['silhouette']['2']:.2f}); documented shape "
             f"is associated but not recovered (chi-square({C['shape_test']['df']})="
             f"{C['shape_test']['chi2']:.0f}, p<0.001, V={C['shape_test']['cramers_v']:.2f})",
             x=0.01, ha="left", fontsize=8.1, y=1.14)
save(fig, "fig21_pattern_clusters.png")

# ============================================================== 22. PTA variants
pv = J["pta_variants"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]
bins = np.arange(0, 127, 5)
for key, lab, col, ls, mk in [("pta3", "PTA-3 (0.5/1/2 kHz)", F.BLUE, "-", "o"),
                              ("pta4", "PTA-4 (0.5/1/2/4 kHz)", F.TEAL, "--", "s"),
                              ("pta8", "Mean of 250 Hz to 8 kHz", F.ORANGE, ":", "^")]:
    ax.hist(df[key], bins=bins, histtype="step", lw=1.6, color=col, ls=ls,
            label=f"{lab}: median {pv[key]['median']:.1f}")
    ax.axvline(pv[key]["median"], color=col, lw=1, ls=ls)
ax.set_xlabel("Average threshold (dB HL)")
ax.set_ylabel("Ears")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.19), ncol=1, fontsize=7,
          frameon=False)
ax.set_xlim(0, 125)
ax.set_ylim(0, 54)          # headroom so the legend clears the curve peaks
F.title(ax, "Three ways to average the audiogram", "overlaid, shared 5 dB bins")

ax = axes[1]
g3 = pv["grade_change_pta3_vs_pta4"]
g8 = pv["grade_change_pta8_vs_pta4"]
x = np.arange(2)
vals = [100 * g3["pct_changed"], 100 * g8["pct_changed"]]
bars = ax.bar(x, vals, color=[F.BLUE, F.ORANGE], alpha=0.85, width=0.55, hatch=["", "//"])
for i, (v, gn) in enumerate(zip(vals, [g3, g8])):
    ax.text(i, v + 1, f"{gn['n_changed']} ears\n{v:.1f}%", ha="center", fontsize=7.4)
ax.set_xticks(x)
ax.set_xticklabels(["PTA-3 vs PTA-4", "8-frequency vs PTA-4"], fontsize=7.6)
ax.set_ylabel("Ears whose Clark grade changes (%)")
ax.set_ylim(0, 40)
ax.text(0.02, 0.97, "direction of change (PTA-3 vs PTA-4):\n"
        f"{g3['table'].get('-1', 0)} one grade less severe, {g3['table'].get('1', 0)} one grade more severe",
        transform=ax.transAxes, fontsize=6.9, color=F.MUTED, va="top")
F.title(ax, "How much the average matters", "grade change under the Clark cuts")
save(fig, "fig22_pta_variants.png")

# ============================================================== 23. AC vs BC, reverse gaps
AB = J["abg"]
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.5), gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.30})
ax = axes[0]
rev_ids = set(AB["reverse_gt20_ids"])
rows = []
for bc, ac, lab, mk, col in zip(BC, BC_AC, BCLAB, F.MARKERS, [F.BLUE, F.TEAL, F.ORANGE, F.SAND]):
    m = df[[ac, bc]].dropna()
    ax.scatter(m[ac] + np.random.default_rng(1).normal(0, 0.7, len(m)),
               m[bc] + np.random.default_rng(2).normal(0, 0.7, len(m)),
               s=7, marker=mk, facecolor="none", edgecolor=col, lw=0.6, alpha=0.5,
               label=f"{lab} Hz")
    for _, r in m.iterrows():
        rows.append((r[ac], r[bc], lab))
ax.plot([-15, 125], [-15, 125], color=F.INK, lw=1, ls=":")
ax.plot([-15, 105], [5, 125], color=F.GREY, lw=0.9, ls="--")
ax.plot([5, 125], [-15, 105], color=F.GREY, lw=0.9, ls="--")
ax.set_xlabel("Air-conduction threshold (dB HL)")
ax.set_ylabel("Bone-conduction threshold (dB HL)")
ax.set_xlim(-12, 128); ax.set_ylim(-12, 128)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.21), ncol=4, title="frequency",
          title_fontsize=7, fontsize=7.2, frameon=False, columnspacing=1.4)
F.title(ax, "Air against bone conduction, all four BC frequencies",
        "dotted = identity; dashed bands = ±10 dB protocol tolerance (n = 1,603 pairs)")

ax = axes[1]
ax.axis("off")
lines = [f"{'Study':>6} {'Hz':>5} {'AC':>4} {'BC':>4} {'BC-AC':>6}"]
det = df[df.flag_bc_gt_ac_20 == 1].copy()
det["worst"] = det[["bc_500", "bc_1k", "bc_2k", "bc_4k"]].values.max(1) - \
    det[["th_500", "th_1k", "th_2k", "th_4k"]].values.min(1)
for _, r in det.sort_values("max_bc_minus_ac", ascending=False).iterrows():
    gap = np.asarray(r[BC].values, float) - np.asarray(r[BC_AC].values, float)
    j = int(np.nanargmax(gap))
    lines.append(f"{int(r.study_id):>6} {BCLAB[j]:>5} {float(r[BC_AC[j]]):>4.0f} "
                 f"{float(r[BC[j]]):>4.0f} {gap[j]:>+6.0f}")
ax.text(0, 1.0, "Ears with BC - AC > 20 dB\n(beyond any physiological explanation)", fontsize=8,
        fontweight="bold", va="top")
ax.text(0, 0.80, "\n".join(lines), fontsize=7.2, family="DejaVu Sans Mono", va="top",
        color=F.INK, linespacing=1.45)
ax.text(0, 0.02, f"59 ears exceed +10 dB overall; {AB['reverse_gt20']} exceed +20 dB;\n"
        f"{AB['gap_gt60']} have AC - BC > 60 dB. All are flagged, none dropped.",
        fontsize=7.0, color=F.MUTED, va="bottom", transform=ax.transAxes)
save(fig, "fig23_ac_bc_scatter.png")

# ============================================================== 24. ABG by group
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4), gridspec_kw={"wspace": 0.32})
ax = axes[0]
order = sorted(DIAG_ORDER, key=lambda k: J["abg"]["by_diagnosis"][k].get("median", 0))
groups = [df.loc[df.diagnosis_category == k, "abg_mean"].dropna().values for k in order]
box(ax, groups, ["" for _ in order], [F.ORANGE if k in ("other", "not_documented") else F.BLUE
                                      for k in order], widths=0.6, showfliers=True)
ax.axhline(0, color=F.INK, lw=0.9)
ax.set_xticks(range(len(order)))
ax.set_xticklabels([f"{DIAG_PRETTY[k]} ({len(g)})" for k, g in zip(order, groups)],
                   rotation=35, ha="right", fontsize=6.8)
ax.set_ylabel("Mean air-bone gap, BC - AC (dB)")
ax.set_ylim(-72, 44)
t = J["abg"]["test_diagnosis"]
ax.text(0.02, 0.97, f"Kruskal-Wallis H({t['df']})={t['H']:.1f}, {pfmt(t['p'])}\n"
        f"$\\epsilon^2$={t['epsilon_squared']:.2f}",
        transform=ax.transAxes, fontsize=6.8, va="top",
        bbox=dict(facecolor="white", edgecolor=F.GRID, boxstyle="round,pad=0.3", alpha=0.9))
F.title(ax, "Air-bone gap by aetiology", "negative = conductive component, as expected")

ax = axes[1]
groups = [df.loc[df.consultant_grade == g, "abg_mean"].dropna().values for g in LBL6]
box(ax, groups, PRETTY_SHORT, [F.PALETTE[g] for g in LBL6], widths=0.6, showfliers=True)
for lb in ax.get_xticklabels():
    lb.set_rotation(30); lb.set_ha("right")
ax.axhline(0, color=F.INK, lw=0.9)
ax.set_ylabel("Mean air-bone gap, BC - AC (dB)")
ax.set_ylim(-72, 44)
t = J["abg"]["test_consult"]
ax.text(0.02, 0.97, f"Kruskal-Wallis H({t['df']})={t['H']:.1f}, {pfmt(t['p'])}\n"
        f"$\\epsilon^2$={t['epsilon_squared']:.2f}",
        transform=ax.transAxes, fontsize=6.8, va="top",
        bbox=dict(facecolor="white", edgecolor=F.GRID, boxstyle="round,pad=0.3", alpha=0.9))
F.title(ax, "Air-bone gap by consultant grade", "the profound band is the 120 dB ceiling artefact")
fig.text(0.01, -0.24, "The grade gradient is driven by the profound band, where BC is also recorded at 120 dB "
         "(BC - AC = 0 by construction) and by CSOM/otosclerosis, the two categories with a real conductive "
         "component. A gap is not evidence of error on its own; only the +20 dB reversals are.",
         fontsize=6.9, color=F.MUTED, ha="left", va="top", wrap=True)
save(fig, "fig24_abg_by_group.png")

# ============================================================== 25. diagnosis counts
DG = J["diagnosis"]["counts"]
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.3), gridspec_kw={"width_ratios": [1.35, 1], "wspace": 0.34})
ax = axes[0]
order = sorted(DIAG_ORDER, key=lambda k: DG[k]["ears"])
y = np.arange(len(order))
ears = [DG[k]["ears"] for k in order]
pats = [DG[k]["patients"] for k in order]
cols = [F.ORANGE if k in ("other", "not_documented") else F.BLUE for k in order]
hat = ["xx" if k == "not_documented" else ("//" if k == "other" else "") for k in order]
ax.barh(y, ears, color=cols, alpha=0.85, height=0.62, hatch=hat, edgecolor="white")
for i, (e, p) in enumerate(zip(ears, pats)):
    ax.text(e + 3, i, f"{e} ({100*e/410:.1f}%)  {p} patients", va="center", fontsize=6.8,
            color=F.INK)
ax.set_yticks(y); ax.set_yticklabels([DIAG_PRETTY[k] for k in order], fontsize=7.4)
ax.set_xlabel("Ears")
ax.set_xlim(0, 315)
ax.legend(handles=[Patch(facecolor=F.BLUE, label="Named diagnosis"),
                   Patch(facecolor=F.ORANGE, hatch="//", label="'other' (undefined residual)"),
                   Patch(facecolor=F.ORANGE, hatch="xx", label="not documented")],
          loc="upper right", bbox_to_anchor=(1.0, -0.16), ncol=1, frameon=False)
F.title(ax, "Aetiology after case and spelling normalisation",
        "csoM folded into csom (15 ears); percentages are unweighted ear-level")

ax = axes[1]
named = 100 * J["diagnosis"]["named_pct"]
ax.bar([0], [named], color=F.BLUE, width=0.5, alpha=0.85)
ax.bar([0], [100 - named], bottom=[named], color=F.ORANGE, width=0.5, hatch="..", alpha=0.85,
       edgecolor="white")
ax.text(0, named / 2, f"{named:.1f}%\nnamed", ha="center", va="center", color="white",
        fontsize=8, fontweight="bold")
ax.text(0, named + (100 - named) / 2, f"{100-named:.1f}%\nresidual or\nnot documented", ha="center",
        va="center", fontsize=7.4, color=F.INK)
ax.set_xlim(-0.6, 0.6); ax.set_ylim(0, 100)
ax.set_xticks([]); ax.set_ylabel("Share of ears (%)")
t = J["diagnosis"]["pta_test"]
ax.text(0.0, -0.03, f"PTA-4 differs across categories:\nH({t['df']})={t['H']:.1f}, {pfmt(t['p'])},\n"
        f"$\\epsilon^2$={t['epsilon_squared']:.2f}", fontsize=6.5, color=F.MUTED, ha="left", va="top",
        transform=ax.transAxes)
F.title(ax, "How much aetiology is actually known", "55.9% of ears carry no usable label")
save(fig, "fig25_diagnosis_counts.png")

# ============================================================== 26. shape cross-tabs
SH = J["shape"]
fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.3), gridspec_kw={"wspace": 0.42})
ax = axes[0]
cols = SH["fai_cols"]
M = np.array([[SH["fai_table"][r][cols.index(c)] for c in cols] for r in ["Flat", "Sloping", "Rising", "Notched"]])
im = ax.imshow(M, cmap="Blues", aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        if M[i, j]:
            ax.text(j, i, int(M[i, j]), ha="center", va="center", fontsize=7.4,
                    color="white" if M[i, j] > M.max() * 0.55 else F.INK)
ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=30, ha="right", fontsize=7)
ax.set_yticks(range(4)); ax.set_yticklabels(["Flat", "Sloping", "Rising", "Notched"], fontsize=7.4)
ax.set_xlabel("Configuration computed by the FAI")
ax.set_ylabel("Documented shape")
ax.grid(False)
ax.set_title(f"Documented vs FAI:\n{100*SH['fai_exact']:.1f}% exact (n={SH['fai_n']}), "
             f"kappa {SH['fai_kappa']:.2f}", loc="left", fontsize=8.4, fontweight="bold")

ax = axes[1]
cols2 = ["flat", "sloping", "rising", "notched", "undetermined"]
M2 = np.array([[SH["derived_table"][r][cols2.index(c)] + (SH["derived_table"][r][cols2.index(c)] // 100)
                for c in cols2] for r in ["flat", "sloping", "rising", "notched"]])
M2 = np.array([[SH["derived_table"][r][cols2.index(c)] for c in cols2]
               for r in ["flat", "sloping", "rising", "notched"]])
im = ax.imshow(M2, cmap="Blues", aspect="auto")
for i in range(M2.shape[0]):
    for j in range(M2.shape[1]):
        if M2[i, j]:
            ax.text(j, i, int(M2[i, j]), ha="center", va="center", fontsize=7.4,
                    color="white" if M2[i, j] > M2.max() * 0.55 else F.INK)
ax.set_xticks(range(len(cols2)))
ax.set_xticklabels(["Flat", "Sloping", "Rising", "Notched", "Undet."], rotation=30, ha="right",
                   fontsize=7)
ax.set_yticks(range(4)); ax.set_yticklabels(["Flat", "Sloping", "Rising", "Notched"], fontsize=7.4)
ax.set_xlabel("Configuration from a transparent threshold rule")
ax.grid(False)
ax.set_title(f"Documented vs threshold rule:\n{100*SH['derived_exact']:.1f}% exact", loc="left",
             fontsize=8.4, fontweight="bold")
fig.text(0.01, -0.24, "Two independent automatic schemes agree with the documented label at almost the "
         "same rate (42.7% and 42.3%). The documented shapes are therefore not recoverable from the "
         "threshold vector by either route: 111 of the 116 documented 'notched' ears are not called "
         "notched by the FAI.", fontsize=6.9, color=F.MUTED, ha="left", va="top", wrap=True)
save(fig, "fig26_shape_crosstab.png")

# ============================================================== 27. consultant vs computed
CL = J["consultant"]
fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.4), gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.44})
ax = axes[0]
M = np.array([[CL["vs_clark"][r][i] for i in range(6)] for r in LBL6])
im = ax.imshow(M, cmap="Blues", aspect="auto")
for i in range(6):
    for j in range(6):
        if M[i, j]:
            ax.text(j, i, int(M[i, j]), ha="center", va="center", fontsize=7.2,
                    color="white" if M[i, j] > M.max() * 0.55 else F.INK)
ax.set_xticks(range(6)); ax.set_xticklabels(PRETTY_SHORT, rotation=35, ha="right", fontsize=7)
ax.set_yticks(range(6)); ax.set_yticklabels(PRETTY_SHORT, fontsize=7)
ax.set_xlabel("Clark grade from PTA-4")
ax.set_ylabel("Consultant grade")
ax.grid(False)
ax.set_title(f"Consultant vs Clark: {100*CL['vs_clark_exact']:.1f}% exact, "
             f"kappa {CL['vs_clark_kappa']:.3f}", loc="left", fontsize=8.4, fontweight="bold")

ax = axes[1]
signed = CL["vs_clark_signed"]
ks = sorted(int(k) for k in signed)
vals = [signed[str(k)] for k in ks]
ax.bar(ks, vals, color=[F.ORANGE if k else F.BLUE for k in ks], width=0.62, alpha=0.88,
       hatch=["//" if k else "" for k in ks], edgecolor="white")
for k, v in zip(ks, vals):
    ax.text(k, v + 3, str(v), ha="center", fontsize=7.2)
ax.set_xticks(ks)
ax.set_xlabel("Consultant grade minus Clark grade (steps)")
ax.set_ylabel("Ears")
ax.set_ylim(0, max(vals) * 1.38)
_near = sum(M[i, j] for i in range(6) for j in range(6) if abs(i - j) <= 1)
ax.text(0.98, 0.95, f"exact {100*M.trace()/M.sum():.1f}%, within one grade "
        f"{100*_near/M.sum():.1f}%\nn = {int(M.sum())} ears",
        transform=ax.transAxes, fontsize=6.9, va="top", ha="right", color=F.INK)
F.title(ax, "Direction of departure", "positive = consultant grades more severe than PTA-4")
fig.text(0.01, -0.13, "Departures are almost all one step and one-directional: the consultant reads "
         "'mild' where PTA-4 says normal (37 ears) and 'moderately severe' where PTA-4 says moderate "
         "(10 ears). This is a threshold convention, not random disagreement.",
         fontsize=6.9, color=F.MUTED, ha="left", va="top", wrap=True)
save(fig, "fig27_consultant_vs_computed.png")

# ============================================================== 28. boundary proximity by scheme
fig, ax = plt.subplots(figsize=(7.4, 3.4))
for (key, col, ls, mk), lab in zip([("clark", F.BLUE, "-", "o"), ("who5", F.TEAL, "--", "s"),
                                    ("who21", F.ORANGE, ":", "^")],
                                   ["Clark / protocol WHO (6)", "WHO 1997 (5, shipped script)",
                                    "WHO 2021 (7)"]):
    d = J["boundary"][key]
    xs = [0, 1, 2, 5, 10, 15]
    ys = [0, d["pct_within_1"], d["pct_within_2"], d["pct_within_5"], d["pct_within_10"],
          d["pct_within_window"]]
    ax.plot(xs, [100 * v for v in ys], marker=mk, ls=ls, color=col, ms=4, label=lab)
for x0, lab in [(2, "±2 dB"), (5, "±5 dB"), (10, "±10 dB")]:
    ax.axvline(x0, color=F.GREY, lw=0.8, ls=":")
    ax.text(x0 + 0.28, 101.5, lab, fontsize=6.6, color=F.MUTED, ha="left", va="top")
d = J["boundary"]
# each label sits clear of its own line: above for the upper two series, below for the middle one
_lab = {"clark": (-3, 4, "bottom"), "who5": (2, -4, "top"), "who21": (2, 5, "bottom")}
for key, col in [("clark", F.BLUE), ("who5", F.TEAL), ("who21", F.ORANGE)]:
    dd = d[key]
    dx, dy, va = _lab[key]
    ax.annotate(f"{100*dd['pct_within_5']:.1f}%", (5, 100 * dd["pct_within_5"]),
                textcoords="offset points", xytext=(dx, dy),
                ha="right" if dx < 0 else "left", va=va, fontsize=6.8, color=col)
ax.set_xlabel("Distance from the nearest grade boundary (dB)")
ax.set_ylabel("Ears within that distance (%)")
ax.set_xlim(0, 16); ax.set_ylim(0, 105)
ax.legend(loc="lower right")
F.title(ax, "Boundary proximity under each reference scheme",
        "at ±5 dB: Clark 57.6%, WHO 1997 50.7%, WHO 2021 66.3% of ears are borderline")
save(fig, "fig28_boundary_by_scheme.png")

# ============================================================== 29. three schemes side by side
fig, ax = plt.subplots(figsize=(7.4, 3.2))
SC = J["schemes"]
levels = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound", "complete"]
series = [("Clark / WHO-6", SC["clark"], F.BLUE, "-", "o", ""),
          ("WHO 1997 (5)", SC["who5"], F.TEAL, "--", "s", "//"),
          ("WHO 2021 (7)", SC["who21"], F.ORANGE, ":", "^", "..")]
w = 0.26
x = np.arange(len(levels))
for i, (lab, d, col, ls, mk, h) in enumerate(series):
    vals = [d.get(g, 0) for g in levels]
    ax.bar(x + (i - 1) * w, vals, w, color=col, alpha=0.85, hatch=h, edgecolor="white", label=lab)
    for xx, v in zip(x + (i - 1) * w, vals):
        if v:
            ax.text(xx, v + 2, str(v), ha="center", fontsize=6.2, rotation=90, va="bottom")
ax.set_xticks(x)
ax.set_xticklabels(["Normal", "Mild", "Moderate", "Mod-sev", "Severe", "Profound", "Complete"], fontsize=7.4)
ax.set_ylabel("Ears")
ax.set_ylim(0, 122)
ax.legend(ncol=3, loc="upper left")
fig.text(0.01, -0.10, "Clark and the protocol's six-grade WHO scheme use identical cuts (25/40/55/70/90), "
         "so 0 ears differ and one set of bars serves both. A scheme has no bar at a grade it does not "
         "define: the five-grade scheme has no 'moderately severe' band, and 'complete' exists only in "
         "WHO 2021.",
         fontsize=6.9, color=F.MUTED, ha="left", va="top", wrap=True)
F.title(ax, "Grade distributions under the three schemes computed from PTA-4",
        "the five-grade scheme has no 'moderately severe' band: its 79 ears split 25 to moderate, 54 to severe")
save(fig, "fig29_scheme_grade_bars.png")

# ============================================================== 30. FAI confusion matrices
CF = J["confusion"]
fig, axes = plt.subplots(1, 3, figsize=(7.8, 3.6), gridspec_kw={"wspace": 0.55})
fig.subplots_adjust(bottom=0.26)
for ax, key, title in zip(axes, ["clark", "who5", "who21"],
                          ["vs Clark / WHO-6", "vs WHO 1997 (5)", "vs WHO 2021 (7)"]):
    c = CF[key]
    M = np.array(c["matrix"])
    im = ax.imshow(M, cmap="Blues", aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if M[i, j]:
                ax.text(j, i, int(M[i, j]), ha="center", va="center",
                        fontsize=6.4, color="white" if M[i, j] > M.max() * 0.55 else F.INK)
    k = len(c["labels"])
    ax.set_xticks(range(k)); ax.set_xticklabels([PRETTY_SHORT[:k][i] if k == 6 else
                                                 (["Normal", "Mild", "Mod", "Sev", "Prof"][i] if k == 5
                                                  else ["Norm", "Mild", "Mod", "M-S", "Sev", "Prof", "Comp"][i])
                                                 for i in range(k)], rotation=45, ha="right", fontsize=6)
    ax.set_yticks(range(k)); ax.set_yticklabels(["N", "Mi", "Mo", "MS", "S", "P", "C"][:k], fontsize=6.4)
    ax.grid(False)
    ax.set_xlabel("FAI label", fontsize=7.4)
    ax.set_title(f"{title}\nn={c['n']}, exact {100*c['exact']:.1f}%", loc="left",
                 fontsize=7.8, fontweight="bold")
    ax.text(0.5, -0.40, f"$\\kappa_q$={c['kappa_quad']:.3f} (95% CI {c['kappa_ci'][0]:.3f} to "
            f"{c['kappa_ci'][1]:.3f})", transform=ax.transAxes, ha="center", fontsize=6.4,
            color=F.INK)
axes[0].set_ylabel("Reference grade", fontsize=7.4)
fig.text(0.01, -0.22, "Rows are the reference grade, columns the FAI label. 107 ears are graded higher "
         "by the FAI than by Clark and 12 lower; against WHO 2021 the direction reverses (63 higher, "
         "109 lower) because that scheme has an extra band above 95 dB.",
         fontsize=6.9, color=F.MUTED, ha="left", va="top", wrap=True)
save(fig, "fig30_fai_confusion.png")

# ============================================================== 31. Bland-Altman
BA = J["bland_altman"]
ok = df[df.ok].copy()
ok["diff"] = ok.fai_score - ok.pta4
ok["mean"] = (ok.fai_score + ok.pta4) / 2
fig, ax = plt.subplots(figsize=(7.2, 3.5))
m120 = ok.flag_120_any_freq.astype(bool)
ax.scatter(ok.loc[~m120, "mean"], ok.loc[~m120, "diff"], s=13, marker="o", facecolor="none",
           edgecolor=F.BLUE, lw=0.7, alpha=0.7, label=f"No 120 dB value, n={int((~m120).sum())}")
ax.scatter(ok.loc[m120, "mean"], ok.loc[m120, "diff"], s=18, marker="^", facecolor=F.ORANGE,
           edgecolor="white", lw=0.4, alpha=0.9, label=f"Carries a 120 dB value, n={int(m120.sum())}")
ax.axhline(BA["bias"], color=F.INK, lw=1.3, ls="-")
for v, lab, ls in [(BA["loa_high"], "upper LoA", "--"), (BA["loa_low"], "lower LoA", "--")]:
    ax.axhline(v, color=F.MUTED, lw=1.0, ls=ls)
ax.axhline(0, color=F.GREY, lw=0.8, ls=":")
xs = np.linspace(0, 110, 40)
o = BA["slope_vs_mean"]
ax.plot(xs, o["intercept"] + o["slope"] * xs, color=F.TEAL, lw=1.5, ls="-.",
        label=f"trend in the difference: {o['slope']:+.3f} per dB")
ax.set_xlabel("Mean of FAI score and PTA-4 (dB)")
ax.set_ylabel("FAI score minus PTA-4 (dB)")
ax.set_ylim(-30, 30); ax.set_xlim(0, 110)
ax.legend(loc="lower left", ncol=1)
ax.text(0.985, 0.96, f"bias {BA['bias']:+.2f} dB\n95% limits {BA['loa_low']:+.1f} to "
        f"{BA['loa_high']:+.1f} dB\n{100*BA['pct_within_5']:.0f}% within ±5 dB",
        transform=ax.transAxes, ha="right", va="top", fontsize=7,
        bbox=dict(facecolor="white", edgecolor=F.GRID, boxstyle="round,pad=0.35"))
F.title(ax, "FAI score against PTA-4: calibration, not noise",
        "the FAI reads 2.9 dB low on average and the offset widens with severity")
fig.text(0.01, -0.10, f"Mean bias by band: normal {BA['by_grade']['normal']['mean_bias']:+.1f}, "
         f"mild {BA['by_grade']['mild']['mean_bias']:+.1f}, moderate {BA['by_grade']['moderate']['mean_bias']:+.1f}, "
         f"mod-severe {BA['by_grade']['moderately_severe']['mean_bias']:+.1f}, "
         f"severe {BA['by_grade']['severe']['mean_bias']:+.1f}, profound {BA['by_grade']['profound']['mean_bias']:+.1f} dB. "
         f"The score saturates at {BA['saturation']['max_score']:.1f}, above which {BA['saturation']['n_score_gt94']} ears "
         f"cannot be separated although {BA['saturation']['n_pta_gt95']} have PTA-4 above 95 dB.",
         fontsize=6.9, color=F.MUTED, ha="left", va="top", wrap=True)
save(fig, "fig31_bland_altman.png")

# ============================================================== 32. agreement by grade
AG = J["by_grade"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), gridspec_kw={"wspace": 0.30})
ax = axes[0]
x = np.arange(6)
ex = [100 * AG[g]["exact"] for g in LBL6]
lo = [max(0.0, 100 * (AG[g]["exact"] - AG[g]["ci"][0])) for g in LBL6]
hi = [max(0.0, 100 * (AG[g]["ci"][1] - AG[g]["exact"])) for g in LBL6]
ax.bar(x, ex, color=[F.PALETTE[g] for g in LBL6], width=0.62, edgecolor=F.MUTED, lw=0.6)
ax.errorbar(x, ex, yerr=[lo, hi], fmt="none", ecolor=F.INK, elinewidth=1, capsize=3)
for i, (g, v) in enumerate(zip(LBL6, ex)):
    ax.text(i, 3, f"n={AG[g]['n']}", ha="center", fontsize=6.4, color="white" if v > 30 else F.INK)
    ax.text(i, v + hi[i] + 3.0, f"{v:.0f}%", ha="center", fontsize=7, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(PRETTY_SHORT, rotation=30, ha="right")
ax.set_ylabel("Exact agreement (%)")
ax.set_ylim(0, 112)
F.title(ax, "Agreement by reference grade", "bars: exact agreement, whiskers: 95% Wilson CI")

ax = axes[1]
bias = [AG[g]["mean_signed_error"] for g in LBL6]
ax.bar(x, bias, color=[F.ORANGE if b > 0 else F.BLUE for b in bias], width=0.62, alpha=0.88,
       hatch=["//" if b > 0 else "" for b in bias], edgecolor="white")
for i, b in enumerate(bias):
    ax.text(i, b + (0.04 if b >= 0 else -0.04), f"{b:+.2f}", ha="center",
            va="bottom" if b >= 0 else "top", fontsize=7)
ax.axhline(0, color=F.INK, lw=0.9)
ax.set_xticks(x); ax.set_xticklabels(PRETTY_SHORT, rotation=30, ha="right")
ax.set_ylabel("Mean grade error (FAI minus reference)")
ax.set_ylim(-0.35, 1.0)
F.title(ax, "Where the disagreement sits", "positive = FAI grades one step too severe")
fig.text(0.01, -0.12, "Two thirds of all disagreement (107 of 119 off-grade ears) is concentrated in "
         "'moderate' and 'moderately severe', where the FAI calls 44 of 67 and 57 of 76 ears one grade "
         "worse. Agreement is at or near 100% in normal, severe and profound.", fontsize=6.9,
         color=F.MUTED, ha="left", va="top", wrap=True)
save(fig, "fig32_agreement_by_grade.png")

# ============================================================== 33. missingness by ear and diagnosis
MS = J["missing_ext"]
fig, axes = plt.subplots(1, 2, figsize=(7.8, 2.9), gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.34})
cols = AC + BC
lab = [f"{f}" for f in FREQLAB] + ["BC.5", "BC1", "BC2", "BC4"]
ax = axes[0]
M = np.array([[100 * MS["by_ear"][e][c] for c in cols] for e in ("left", "right")])
im = ax.imshow(M, cmap="bone_r", vmin=0, vmax=100, aspect="auto")
for i in range(2):
    for j in range(len(cols)):
        if M[i, j] > 0:
            ax.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if M[i, j] > 55 else F.INK)
ax.set_yticks([0, 1]); ax.set_yticklabels(["Left", "Right"])
ax.tick_params(axis="y", pad=2)
ax.set_xticks(range(len(cols))); ax.set_xticklabels(lab, rotation=45, ha="right", fontsize=6.8)
ax.grid(False)
F.title(ax, "By ear", f"3 kHz {100*MS['by_ear']['left']['th_3k']:.1f}% missing on both sides "
        f"(chi-square {pfmt(MS['test_3k_by_ear']['p'])})")

ax = axes[1]
M2 = np.array([[100 * MS["by_diagnosis"][d][c] for c in cols] for d in DIAG_ORDER])
im = ax.imshow(M2, cmap="bone_r", vmin=0, vmax=100, aspect="auto")
for i in range(len(DIAG_ORDER)):
    for j in range(len(cols)):
        if M2[i, j] > 0:
            ax.text(j, i, f"{M2[i,j]:.0f}", ha="center", va="center", fontsize=6.2,
                    color="white" if M2[i, j] > 55 else F.INK)
ax.set_yticks(range(len(DIAG_ORDER)))
ax.set_yticklabels([DIAG_PRETTY[d] for d in DIAG_ORDER], fontsize=6.8)
ax.set_xticks(range(len(cols))); ax.set_xticklabels(lab, rotation=45, ha="right", fontsize=6.8)
ax.grid(False)
F.title(ax, "By aetiology category")
cb = fig.colorbar(im, ax=axes[1], fraction=0.03, pad=0.02)
cb.set_label("% missing", fontsize=6.8)
fig.text(0.01, -0.30, f"3 kHz missingness differs by aetiology (chi-square({MS['test_3k_by_diagnosis']['df']})="
         f"{MS['test_3k_by_diagnosis']['chi2']:.1f}, {pfmt(MS['test_3k_by_diagnosis']['p'])}), but the association "
         "is collinear with testing year: the field stops being recorded in mid-2022, and categories are "
         "not evenly spread across years. Read the right panel as a calendar artefact, not a clinical one.",
         fontsize=6.8, color=F.MUTED, ha="left", va="top", wrap=True)
save(fig, "fig33_missingness_by_ear_diagnosis.png")

# ============================================================== 34. 120 dB ceiling vs 8 kHz
CD = J["ceiling"]
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.3), gridspec_kw={"wspace": 0.30})
ax = axes[0]
x = np.arange(8)
n120 = [CD["cells_120"][str(f)] for f in FREQ]
ax.bar(x, n120, color=[F.ORANGE if f == 8000 else F.BLUE for f in FREQ], width=0.62, alpha=0.88,
       hatch=["//" if f == 8000 else "" for f in FREQ], edgecolor="white")
for i, v in enumerate(n120):
    ax.text(i, v + 0.8, str(v), ha="center", fontsize=7)
ax.axhspan(0, 0, color="none")
ax.set_xticks(x); ax.set_xticklabels(FREQLAB)
ax.set_ylabel("Cells recorded at exactly 120 dB HL")
ax.set_ylim(0, 46)
ax.set_ylim(0, 62)
F.title(ax, "Where the 120 dB ceiling code appears",
        "143 cells (4.7%) across 54 ears; 25 sit at 8 kHz")

ax = axes[1]
j = np.random.default_rng(5)
ax.scatter(df.th_6k + j.normal(0, 0.6, len(df)), df.th_8k + j.normal(0, 0.6, len(df)), s=8,
           marker="o", facecolor="none", edgecolor=F.GREY, lw=0.6, alpha=0.6, label="Ear")
m = (df.th_6k == 120) & (df.th_8k < 120)
ax.scatter(df.loc[m, "th_6k"], df.loc[m, "th_8k"], s=22, marker="^", facecolor=F.ORANGE,
           edgecolor="white", lw=0.4, label=f"6 kHz = 120, 8 kHz lower (n={int(m.sum())})")
ax.plot([-10, 125], [-10, 125], color=F.INK, lw=1, ls=":")
ax.set_xlabel("6 kHz threshold (dB HL)")
ax.set_ylabel("8 kHz threshold (dB HL)")
ax.set_xlim(-10, 130); ax.set_ylim(-10, 130)
ax.legend(loc="lower right")
F.title(ax, "Impossible orderings at the ceiling",
        f"16 ears also have 120 at 4 kHz with a lower 8 kHz value")
fig.text(0.01, -0.10, "The 25 ceiling values at 8 kHz are the strongest single indicator that 120 is a "
         "maximum-output code rather than a measured threshold: clinical audiometers typically cannot "
         "deliver 120 dB HL at 8 kHz. The right panel adds the ordering argument, since a patient cannot "
         "fail to respond at 120 dB at 6 kHz and then respond at 100 dB at 8 kHz.",
         fontsize=6.9, color=F.MUTED, ha="left", va="top", wrap=True)
save(fig, "fig34_ceiling_8k.png")

# ============================================================== 35. anomaly inventory
AN = pd.DataFrame(J["anomalies"])
order_by = {"fix before analysis": 0, "query": 1, "review": 2, "limitation": 3, "fixable": 4, "pass": 5}
AN["o"] = AN.disposition.map(order_by)
AN = AN.sort_values(["o", "n"], ascending=[True, True]).reset_index(drop=True)
COL = {"query": F.ORANGE, "fix before analysis": F.SAND, "review": F.TEAL, "limitation": F.BLUE,
       "fixable": "#7ea6c6", "pass": F.GREY}
MKS = {"query": "s", "fix before analysis": "X", "review": "^", "limitation": "o",
       "fixable": "D", "pass": "P"}
HAT = {"query": "//", "fix before analysis": "xx", "review": "..", "limitation": "", "fixable": "",
       "pass": ""}
fig, ax = plt.subplots(figsize=(7.4, 4.3))
y = np.arange(len(AN))
for i, r in AN.iterrows():
    ax.plot([0.6, max(r.n, 0.6)], [i, i], color=COL[r.disposition], lw=1.1, alpha=0.65, zorder=1)
for i, r in AN.iterrows():
    ax.scatter(max(r.n, 0.6), i, s=44, marker=MKS[r.disposition], c=COL[r.disposition],
               edgecolor="white", lw=0.6, zorder=3)
for i, r in AN.iterrows():
    ax.text(max(r.n, 0.6) * 1.18, i, f"{int(r.n)}", va="center", fontsize=6.6, color=F.INK)
ax.set_yticks(y); ax.set_yticklabels(AN.label, fontsize=7.0)
ax.set_xscale("log")
ax.set_xlim(0.5, 1200)
ax.set_xticks([1, 2, 5, 10, 20, 50, 100, 200, 400])
ax.set_xticklabels(["1", "2", "5", "10", "20", "50", "100", "200", "400"])
ax.set_xlabel("Ears (or cells, where noted in the report table); log scale")
ax.grid(axis="y", visible=False)
handles = [Line2D([], [], marker=MKS[k], color=COL[k], ls="", label=k, markersize=5)
           for k in ["fix before analysis", "query", "review", "limitation", "fixable", "pass"]]
ax.legend(handles=handles, loc="lower right", ncol=2, fontsize=6.6)
F.title(ax, "Anomaly inventory with disposition",
        "orange = must go back to the data collector; grey = checked and passed")
save(fig, "fig35_anomaly_counts.png")

print("extended figures complete:", len(list(FIG.glob("fig*.png"))), "files in figures/")
