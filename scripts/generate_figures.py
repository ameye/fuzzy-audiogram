#!/usr/bin/env python3
"""Generate the manuscript figures from the committed Ruspini analysis.

Every figure is drawn from a committed output:

* ``data/output_participant/predictions_participant.pkl`` -- held-out test ears
* ``data/output_participant/metrics_participant.json``    -- headline metrics
* ``data/output_participant/manuscript_numbers.json``     -- derived tables
* ``data/output_participant/cohort_stats.json``           -- cohort description

Figures 3, 5 and 6 were previously drawn from invented curves and a hand-typed
confusion matrix while their captions claimed the held-out test set. They are
now computed from the predictions the pipeline wrote. Figure 7 is explicitly a
set of stated scenarios passed through the FIS, not cohort data, and the caption
says so.

Writes PNG + PDF (and SVG where useful) to figures/.
"""
import json
import pickle
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import accuracy_score, confusion_matrix

import skfuzzy as fuzz
from fuzzy_audiogram import core
from fuzzy_audiogram.cases import CASES, TITLES
from fuzzy_audiogram.ruspini import SEVERITY_ORDER, partition_sum, trapmf

FIGS_DIR = PROJECT / "figures"
FIGS_DIR.mkdir(exist_ok=True)
OUT = PROJECT / "data" / "output_participant"

NUM = json.loads((OUT / "manuscript_numbers.json").read_text(encoding="utf-8"))
MET = json.loads((OUT / "metrics_participant.json").read_text(encoding="utf-8"))
D = pickle.load(open(OUT / "predictions_participant.pkl", "rb"))
PARAMS = MET["mf_params"]
CATS = ["Normal", "Mild", "Moderate", "Moderately Severe", "Severe", "Profound"]
COLOURS = ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#9b59b6", "#2c3e50"]

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 9,
    "figure.dpi": 300,
})


def _save(fig, stem, svg=False, pdf=True):
    png = FIGS_DIR / f"{stem}.png"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    if pdf:
        fig.savefig(FIGS_DIR / f"{stem}.pdf", bbox_inches="tight")
    if svg:
        fig.savefig(FIGS_DIR / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {png.name}")
    return png


# =====================================================================
# FIGURE 1 — Ruspini membership functions + the sum-to-one check
# =====================================================================
def fig1_membership_functions():
    """Six trapezoids that partition 0-120 dB HL, with the partition check."""
    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [2.35, 1.0]})

    universe = np.arange(0, 121, 1)

    for i, cat in enumerate(SEVERITY_ORDER):
        mf = fuzz.trapmf(universe, PARAMS[cat])
        ax.plot(universe, mf, color=COLOURS[i], linewidth=2.5, label=CATS[i])
        ax.fill_between(universe, mf, 0, alpha=0.08, color=COLOURS[i])

    # Shade the normal-mild transition band, the one the text quantifies.
    ax.axvspan(16.4, 30.0, alpha=0.09, color="#e74c3c")
    ax.annotate("normal–mild\ntransition\n13.6 dB", xy=(23.2, 0.5), xytext=(6.0, 0.62),
                fontsize=8.5, color="#c0392b", ha="center",
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1))

    ax.set_xlabel("Hearing threshold (dB HL)")
    ax.set_ylabel("Membership degree")
    ax.set_title("Six severity memberships form a Ruspini partition", fontweight="bold")
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 1.06)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=6,
              fontsize=8.5, frameon=False)
    ax.grid(True, alpha=0.2)

    # The property itself: sum == 1 everywhere, endpoints included.
    xs = np.linspace(0, 120, 1201)
    sums = np.array([partition_sum(PARAMS, x) for x in xs])
    ax2.plot(xs, sums, color="#2c3e50", linewidth=2)
    ax2.axhline(1.0, color="#2ecc71", linestyle="--", linewidth=1.4)
    ax2.set_ylim(0, 1.12)
    ax2.set_xlim(0, 120)
    ax2.set_xlabel("Hearing threshold (dB HL)")
    ax2.set_ylabel("$\\sum_i \\mu_i(x)$")
    ax2.set_title("Sum of memberships", fontweight="bold")
    rep = NUM["partition"]
    ax2.text(0.5, 0.30,
             f"min = max = 1.000\n{rep['points_checked']:,} points\n"
             f"{rep['n_offending']} failures",
             transform=ax2.transAxes, ha="center", fontsize=9,
             bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                       edgecolor="#cccccc"))
    ax2.grid(True, alpha=0.2)

    fig.tight_layout()
    return _save(fig, "fig1_membership_functions")


# =====================================================================
# FIGURE 2 — FIS architecture schematic
# =====================================================================
def fig2_fis_architecture(n_rules=None, outdir=None, stem="fig2_fis_architecture"):
    """Schematic block diagram labelled with the rule count the code builds."""
    if n_rules is None:
        n_rules = len(list(core.build_audiogram_fis(single_ear=True)[0].rules))

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis("off")

    c_input, c_fuzz, c_rules = "#3498db", "#2ecc71", "#e74c3c"
    c_defuzz, c_output, c_arrow = "#e67e22", "#9b59b6", "#555555"

    def draw_box(x, y, w, h, text, color, subtext=None, fontsize=10):
        rect = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                              boxstyle="round,pad=0.15", facecolor=color,
                              edgecolor="#333", linewidth=1.5, alpha=0.9)
        ax.add_patch(rect)
        ax.text(x, y + (0.1 if subtext else 0), text, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color="white")
        if subtext:
            ax.text(x, y - 0.35, subtext, ha="center", va="center",
                    fontsize=8, color="white", alpha=0.9)

    def draw_arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=c_arrow, lw=2.5))

    row1_y = 6.0
    inputs = ["Threshold\n(500 Hz)", "Threshold\n(1 kHz)", "Threshold\n(2 kHz)",
              "Threshold\n(4 kHz)", "Slope\n(dB/oct)", "Notch\nDepth",
              "Asymmetry\n(inter-aural)"]
    spacing_input = 12.0 / len(inputs)
    for i, inp in enumerate(inputs):
        draw_box(1.0 + i * spacing_input, row1_y, 1.4, 0.7, inp, c_input, fontsize=8)

    fuzz_x, row2_y = 6.5, 4.3
    for i in range(len(inputs)):
        x = 1.0 + i * spacing_input
        draw_arrow(x, row1_y - 0.35, (x + fuzz_x) / 2, row2_y + 0.65)

    draw_box(3.5, row2_y, 5.5, 0.9,
             "Fuzzification\nRuspini trapezoidal MFs",
             c_fuzz, subtext="6 linguistic terms per input")
    draw_arrow(6.25, row2_y, 7.75, row2_y)
    draw_box(9.5, row2_y, 5.5, 0.9,
             f"Mamdani Fuzzy Inference Engine\n{n_rules} Expert-Derived Rules",
             c_rules, subtext="Min–max inference • Implication: minimum")

    row3_y = 1.8
    draw_arrow(3.5, row2_y - 0.55, 3.5, row3_y + 0.75)
    draw_arrow(9.5, row2_y - 0.55, 9.5, row3_y + 0.75)

    draw_box(3.5, row3_y, 5.5, 1.0, "Defuzzification\nCentroid of Area (CoA)",
             c_defuzz, subtext="Aggregation: max-min")
    draw_arrow(6.25, row3_y, 7.75, row3_y)
    draw_box(9.5, row3_y, 5.5, 1.15,
             "Outputs\nFAI (0–100)  •  Configuration Vector\n"
             "Asymmetry Index  •  Linguistic Summary",
             c_output, subtext="Scalar + vector + categorical outputs")

    ax.set_title("Mamdani Fuzzy Inference System Architecture for Audiometric Classification",
                 fontsize=12, fontweight="bold", pad=10)

    for label, lx, ly in [("Inputs", 6.0, 6.7), ("Fuzzification", 3.5, 5.0),
                          ("Rule Engine", 9.5, 5.0), ("Defuzzification", 3.5, 2.5),
                          ("Outputs", 9.5, 2.5)]:
        ax.text(lx, ly, label, ha="center", va="bottom", fontsize=10,
                fontweight="bold", color="#333",
                bbox=dict(facecolor="white", edgecolor="#ccc",
                          boxstyle="round,pad=0.2", alpha=0.8))

    fig.tight_layout()
    out_dir = Path(outdir) if outdir is not None else FIGS_DIR
    path_png = out_dir / f"{stem}.png"
    fig.savefig(path_png, dpi=300, bbox_inches="tight")
    fig.savefig(out_dir / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(out_dir / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path_png.name} ({n_rules} rules)")
    return path_png


# =====================================================================
# FIGURE 3 — Bland-Altman on the held-out test ears
# =====================================================================
def fig3_bland_altman():
    """Bland-Altman of FAI against PTA-4 on the held-out test set.

    Previously this ran the FIS over a synthetic ramp of flat thresholds with
    Gaussian noise added to the reference, while the caption claimed the test
    set. It now plots the 3,913 held-out ears the pipeline scored.
    """
    fai = np.asarray(D["fai"], float)
    pta = np.asarray(D["pta"], float)
    mean = (fai + pta) / 2.0
    diff = fai - pta
    bias = float(MET["bias"])
    lo_lo, lo_hi = float(MET["loa_lo"]), float(MET["loa_hi"])

    fig, ax = plt.subplots(figsize=(8.2, 6))
    ax.scatter(mean, diff, s=9, alpha=0.28, color="#3498db", edgecolors="none",
               label=f"held-out ears (n = {len(fai):,})")
    ax.axhline(bias, color="#e74c3c", linewidth=2, label=f"Bias = {bias:+.1f} dB")
    ax.axhline(lo_hi, color="#e74c3c", linestyle="--", linewidth=1.4,
               label=f"+1.96 SD = {lo_hi:+.1f}")
    ax.axhline(lo_lo, color="#e74c3c", linestyle="--", linewidth=1.4,
               label=f"−1.96 SD = {lo_lo:+.1f}")
    ax.axhline(0, color="gray", linestyle=":", alpha=0.6)
    ax.fill_between([-5, 130], lo_lo, lo_hi, alpha=0.07, color="#e74c3c")

    ax.set_xlabel("Mean of FAI and PTA-4 (dB HL)")
    ax.set_ylabel("FAI − PTA-4 (dB)")
    ax.set_title("Bland-Altman: FAI against PTA-4, held-out test set",
                 fontweight="bold", fontsize=11)
    ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    ax.set_xlim(-5, 125)
    ax.set_ylim(-40, 40)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return _save(fig, "fig3_bland_altman")


# =====================================================================
# FIGURE 4 — clinical case panels
# =====================================================================
def fig4_clinical_cases():
    """Four archetypes from fuzzy_audiogram.cases, with membership bars."""
    freqs = ["250", "500", "1k", "2k", "3k", "4k", "6k", "8k"]
    cats = ["Normal", "Mild", "Mod", "Mod-Sev", "Severe", "Prof"]

    fig, axes = plt.subplots(4, 2, figsize=(13, 12),
                             gridspec_kw={"width_ratios": [1.5, 1.0]})

    bands = [(0, 25, "#2ecc71", "Normal"), (26, 40, "#f1c40f", "Mild"),
             (41, 55, "#e67e22", "Moderate"), (56, 70, "#e74c3c", "Mod-Sev"),
             (71, 90, "#9b59b6", "Severe"), (91, 120, "#2c3e50", "Profound")]

    for row, (key, (_lab, left, right)) in enumerate(CASES.items()):
        ax = axes[row, 0]
        for lo, hi, colour, _name in bands:
            ax.axhspan(lo, hi, alpha=0.13, color=colour)
        ax.plot(range(8), left, "o-", color="#1f4e79", linewidth=2.2, markersize=6,
                markerfacecolor="white", label="ear tested")
        if right is not None:
            ax.plot(range(8), right, "s--", color="#c0392b", linewidth=1.8,
                    markersize=5, markerfacecolor="white", label="contralateral")
        res = core.classify_audiogram(left, right)
        ax.invert_yaxis()
        ax.set_ylim(120, -12)
        ax.set_xlim(-0.5, 7.5)
        ax.set_xticks(range(8))
        ax.set_xticklabels(freqs, fontsize=8)
        ax.set_ylabel("dB HL", fontsize=9)
        ax.set_title(f"{TITLES[key]}  ·  PTA-4 {res['pt4a']:.1f} dB  ·  "
                     f"FAI {res['fai_score']:.1f} ({res['fai_label']})",
                     fontsize=10, fontweight="bold", loc="left")
        ax.grid(True, alpha=0.2)
        if right is not None:
            ax.legend(fontsize=7, loc="lower left")

        axb = axes[row, 1]
        mu = [res["threshold_memberships"][k] for k in SEVERITY_ORDER]
        bars = axb.barh(cats, mu, color=COLOURS, alpha=0.85, edgecolor="#333",
                        linewidth=0.5)
        axb.set_xlim(0, 1.05)
        axb.set_xlabel("Membership degree", fontsize=8)
        axb.tick_params(labelsize=7)
        axb.grid(True, alpha=0.2, axis="x")
        for bar, val in zip(bars, mu):
            if val > 0.02:
                axb.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                         f"{val:.2f}", va="center", fontsize=7)

    fig.suptitle("Clinical case studies: severity membership at PTA-4",
                 fontsize=13, fontweight="bold", y=1.005)
    fig.tight_layout()
    return _save(fig, "fig4_clinical_cases")


# =====================================================================
# FIGURE 5 — agreement against distance from the nearest boundary
# =====================================================================
def fig5_borderline_analysis():
    """Agreement with the crisp grade as a function of distance from a boundary.

    Replaces fitted exponential curves with the observed agreement on the
    held-out ears at every distance from 1 to 15 dB.
    """
    y = np.asarray(D["y_true"]).astype(int)
    yp = np.asarray(D["yf"]).astype(int)
    dist = np.asarray(D["dist"], float)

    xs, agree, ns = [], [], []
    for d in range(1, 16):
        m = np.abs(dist - d) < 0.5
        if m.sum() >= 20:
            xs.append(d)
            agree.append(accuracy_score(y[m], yp[m]) * 100)
            ns.append(int(m.sum()))

    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    ax.axvspan(0.5, 5.5, alpha=0.10, color="#e74c3c", label="borderline zone (±5 dB)")
    ax.plot(xs, agree, "o-", color="#1f4e79", linewidth=2.2, markersize=6,
            label="FAI vs crisp grade")
    ax.axvline(5.5, color="#e74c3c", linestyle="--", alpha=0.5)
    ax.axhline(MET["clear"] * 100, color="#2ecc71", linestyle=":", linewidth=1.5,
               label=f"clear-case agreement {MET['clear']*100:.1f}%")
    for x, a, n in zip(xs, agree, ns):
        if x in (1, 5, 10, 15):
            ax.annotate(f"n={n:,}", (x, a), textcoords="offset points",
                        xytext=(0, -16), ha="center", fontsize=7.5, color="#555")
    ax.set_xlabel("Distance from nearest WHO severity boundary (dB)")
    ax.set_ylabel("Agreement with crisp grade (%)")
    ax.set_title("Borderline analysis on the held-out test set", fontweight="bold",
                 fontsize=11)
    ax.set_ylim(60, 102)
    ax.set_xlim(0, 16)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return _save(fig, "fig5_borderline_analysis")


# =====================================================================
# FIGURE 6 — severity confusion matrix
# =====================================================================
def fig6_confusion_matrix():
    """FIS label against WHO PTA-4 grade on the held-out ears.

    Replaces a hand-typed configuration matrix that was never computed.
    """
    cm = np.array(NUM["confusion_matrix"], int)
    row_sum = cm.sum(axis=1, keepdims=True)
    pct = np.divide(cm, row_sum, out=np.zeros_like(cm, float), where=row_sum > 0) * 100

    fig, ax = plt.subplots(figsize=(7.6, 6.2))
    im = ax.imshow(pct, cmap="Blues", vmin=0, vmax=100)
    for i in range(6):
        for j in range(6):
            if cm[i, j]:
                ax.text(j, i, f"{cm[i, j]}\n{pct[i, j]:.1f}%", ha="center",
                        va="center", fontsize=8.5,
                        color="white" if pct[i, j] > 55 else "#222")
    ax.set_xticks(range(6))
    ax.set_yticks(range(6))
    ax.set_xticklabels(CATS, fontsize=8, rotation=30, ha="right")
    ax.set_yticklabels(CATS, fontsize=8)
    ax.set_xlabel("FAI label (predicted)")
    ax.set_ylabel("WHO PTA-4 grade (reference)")
    ax.set_title(f"Severity agreement, held-out test set (n = {cm.sum():,})\n"
                 f"weighted κ = {MET['kappa']:.3f}, overall {MET['overall']*100:.1f}%",
                 fontsize=10.5, fontweight="bold")
    fig.colorbar(im, ax=ax, shrink=0.75, label="Row percentage")
    fig.tight_layout()
    return _save(fig, "fig6_confusion_matrix")


# =====================================================================
# FIGURE 7 — illustrative FAI trajectories through the FIS
# =====================================================================
def _longitudinal_scenarios():
    """Run three stated annual threshold progressions through the deployed FIS.

    NHANES carries no serial audiometry, so these are defined scenarios rather
    than measured trajectories. The values are written to
    data/output_participant/longitudinal_scenarios.json so the manuscript text
    quotes a committed output rather than the figure.
    """
    scenarios = [
        ("age_related", "Age-related: +0.7 dB/yr at all frequencies",
         [30, 30, 32, 38, 45, 52, 58, 62], 0.7, 8, list(range(7))),
        ("noise_stable", "Noise exposure: stable notch",
         [10, 10, 12, 20, 35, 50, 45, 30], 0.0, 8, []),
        ("ototoxic", "Ototoxic shift: +3 dB/yr at 4-8 kHz",
         [15, 15, 18, 22, 30, 40, 45, 48], 3.0, 4, list(range(3, 7))),
    ]
    out = {}
    for key, title, base, rate, years, idx in scenarios:
        rows = []
        for k in range(years + 1):
            th = list(np.array(base, float))
            for i in idx:
                th[i] = th[i] + rate * k
            res = core.classify_audiogram(np.clip(th, -10, 120))
            rows.append({"year": k, "thresholds": [round(float(v), 1) for v in th],
                         "fai": res["fai_score"], "label": res["fai_label"],
                         "pta4": res["pt4a"]})
        out[key] = {"title": title, "db_per_year": rate, "years": years, "rows": rows}
    (OUT / "longitudinal_scenarios.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    return out


def fig7_longitudinal():
    """FAI trajectories for three stated annual threshold progressions.

    Not cohort data: NHANES has no serial audiometry, so the three scenarios are
    fixed annual shifts passed through the deployed FIS. The point of the panel
    is the shape of the response (continuous FAI against a stepwise PTA grade),
    not a measured rate of change.
    """
    data = _longitudinal_scenarios()
    keys = ["age_related", "noise_stable", "ototoxic"]
    colours = ["#1f4e79", "#c0392b", "#7d3c98"]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, key, colour in zip(axes, keys, colours):
        sc = data[key]
        t = [r["year"] for r in sc["rows"]]
        fai = [r["fai"] for r in sc["rows"]]
        grades = [CATS.index(r["label"]) for r in sc["rows"]]

        ax.plot(t, fai, "o-", color=colour, linewidth=2.4, markersize=6,
                label="FAI (continuous)")
        ax.set_xlabel("Years from baseline")
        ax.set_title(sc["title"], fontsize=10, fontweight="bold")
        ax.set_ylim(0, 60)
        ax.set_xticks(t)
        ax.grid(True, alpha=0.2)
        axes[0].set_ylabel("FAI (0–100)")

        # The crisp label rides a second axis so the step is readable without
        # rescaling the FAI onto an arbitrary numeric scale.
        ax2 = ax.twinx()
        ax2.step(t, grades, "s--", where="mid", color="#777", linewidth=1.8,
                 label="WHO PTA-4 grade")
        ax2.set_ylim(-0.6, 3.4)
        ax2.set_yticks([0, 1, 2, 3])
        ax2.set_yticklabels(["Normal", "Mild", "Moderate", "Mod. Sev."], fontsize=8)
        ax2.set_ylabel("")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")

    fig.suptitle("Illustrative FAI trajectories through the deployed FIS",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "fig7_longitudinal")


def fig_config_fis():
    """Configuration labels the shape rules returned on the held-out ears."""
    dist = MET["config_distribution"]
    order = ["Flat", "Sloping", "Rising", "Precipitous", "Notched", "Undetermined"]
    vals = [dist[k]["share"] * 100 for k in order]
    ns = [dist[k]["n"] for k in order]
    colours = ["#1f4e79", "#2e6da4", "#5b9bd5", "#8fa8c8", "#b0b8c4", "#c0392b"]

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    bars = ax.bar(order, vals, color=colours, edgecolor="#333", linewidth=0.6)
    for bar, v, n in zip(bars, vals, ns):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.8, f"{v:.1f}%\n(n={n})",
                ha="center", fontsize=8.5)
    ax.set_ylabel("Share of held-out ears (%)")
    ax.set_ylim(0, 52)
    ax.set_title(f"FIS configuration labels, n = {sum(ns):,} ears",
                 fontsize=11, fontweight="bold")
    ax.tick_params(axis="x", labelsize=8.5, rotation=20)
    ax.grid(True, alpha=0.2, axis="y")
    fig.tight_layout()
    return _save(fig, "fig_config_fis")


if __name__ == "__main__":
    print("Generating manuscript figures from the committed Ruspini analysis...")
    fig1_membership_functions()
    n = fig2_fis_architecture()
    fig3_bland_altman()
    fig4_clinical_cases()
    fig5_borderline_analysis()
    fig6_confusion_matrix()
    fig7_longitudinal()
    fig_config_fis()
    print(f"\nAll figures written to {FIGS_DIR}/")
