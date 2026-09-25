#!/usr/bin/env python3
"""Generate the four CMPB manuscript figures from committed pipeline outputs.

Why this exists
---------------
The figures shipped with v2/v3 were recovered from an older submission pack and
have no generating script: `grep -rl ija_fig` matches only a zip. For a journal
whose stated criterion is demonstrable, reproducible software, and for a paper
that offers the repository as its implementation, that was the one part of the
manuscript a reviewer could not rebuild. This script closes that gap.

Every quantity is read from the pipeline's own outputs, never typed in:
  data/output_participant/metrics_participant.json   (membership functions,
                                                      calibrated thresholds)
  data/output_participant/manuscript_numbers.json    (case studies, agreement
                                                      by distance from boundary)
  data/output_participant/predictions_participant.pkl (test-set FAI and PTA-4)
  data/output_participant/train_predictions.pkl       (training partition, for
                                                      the Bland-Altman transfer
                                                      and the decision-curve fit)

Corrections carried into the artwork
------------------------------------
  * Bland-Altman maps the FAI onto the decibel scale through a transfer fitted on
    the training partition. The previous figures subtracted a 0-100 index from a
    dB HL quantity and labelled the result decibels.
  * Boundary labels read Clark, not WHO. WHO's own grade tables use five
    categories at 20 dB steps; the six categories at 25/40/55/70/90 dB are
    Clark's.
  * Case D reflects the asymmetry decoupling and is no longer upgraded.

Resolution: 600 dpi, at or above the 3,543 px floor CMPB requires.

Run:  .venv-tools/bin/python scripts/make_cmpb_figures.py
"""
import json, pickle, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("/opt/data/fuzzy-audiogram")
sys.path.insert(0, str(ROOT))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

OUT = ROOT / "data/output_participant"
FIGDIR = ROOT / "cmbp_v2/figures_v3"
FIGDIR.mkdir(parents=True, exist_ok=True)
DPI = 600

MET = json.load(open(OUT / "metrics_participant.json"))
NUM = json.load(open(OUT / "manuscript_numbers.json"))
PARAMS = MET["mf_params"]
LABEL_TH = MET["label_thresholds"]
TEST = pickle.load(open(OUT / "predictions_participant.pkl", "rb"))
TRAIN = pickle.load(open(OUT / "train_predictions.pkl", "rb"))

ORDER = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
NICE = {"normal": "Normal", "mild": "Mild", "moderate": "Moderate",
        "moderately_severe": "Mod. severe", "severe": "Severe", "profound": "Profound"}
COLOURS = ["#1b7837", "#7fbf7b", "#fdb863", "#e08214", "#b2182b", "#542788"]
HATCHES = ["", "///", "\\\\\\", "xxx", "...", "++"]

# The 8 threshold slots run 250, 500, 1k, 2k, 3k, 4k, 6k, 8k Hz.
FREQS = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
PTA_IDX = [1, 2, 3, 5]           # 500, 1k, 2k, 4k — matches compute_audiogram_features
PLOT_IDX = [1, 2, 3, 4, 5, 6, 7]
PLOT_F = [FREQS[i] for i in PLOT_IDX]

plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.linewidth": 0.6,
    "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
})


def trapmf(x, p):
    a, b, c, d = [float(v) for v in p]
    x = np.asarray(x, float)
    y = np.zeros_like(x)
    if b > a:
        m = (x >= a) & (x < b); y[m] = (x[m] - a) / (b - a)
    y[(x >= b) & (x <= c)] = 1.0
    if d > c:
        m = (x > c) & (x <= d); y[m] = (d - x[m]) / (d - c)
    return y


def save(fig, name):
    p = FIGDIR / f"{name}.png"
    fig.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white")
    from PIL import Image
    w, h = Image.open(p).size
    plt.close(fig)
    ok = "PASS" if w >= 3543 else "FAIL"
    print(f"  {name}.png  {w:>5} x {h:<5} px   CMPB >=3543 px: {ok}")
    return p


# ══════════════════════════════════════════════════ Figure 1 — the partition
def figure1():
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    x = np.arange(0, 120.01, 0.05)
    total = np.zeros_like(x)
    for k, cat in enumerate(ORDER):
        y = trapmf(x, PARAMS[cat])
        total += y
        ax.fill_between(x, 0, y, color=COLOURS[k], alpha=0.28,
                        hatch=HATCHES[k], edgecolor=COLOURS[k], linewidth=0.0)
        ax.plot(x, y, color=COLOURS[k], lw=1.5, label=NICE[cat])

    # mark where adjacent shoulders cross: the midpoint of each shared ramp
    for i in range(len(ORDER) - 1):
        a, b = PARAMS[ORDER[i]], PARAMS[ORDER[i + 1]]
        lo, hi = float(b[0]), float(a[3])
        mid = (lo + hi) / 2
        ax.plot([mid], [0.5], "o", ms=3.5, mfc="white", mec="black", mew=0.7, zorder=6)
        ax.annotate(f"{mid:.1f}", (mid, 0.5), textcoords="offset points",
                    xytext=(0, -13), ha="center", fontsize=6)

    ax.axhline(0.5, color="0.6", ls=":", lw=0.6, zorder=1)
    ax.set_xlim(0, 120); ax.set_ylim(0, 1.06)
    ax.set_xlabel("Hearing threshold (dB HL)")
    ax.set_ylabel("Membership degree")
    ax.set_title("Ruspini-partition severity memberships "
                 f"(max deviation of the sum from 1: {np.abs(total - 1).max():.2e})",
                 fontsize=8.5)
    ax.legend(loc="upper center", ncol=6, frameon=False, fontsize=7,
              bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout()
    return save(fig, "fig1_membership_partition")


# ══════════════════════════════════════ Figure 2 — scale-corrected agreement
def figure2():
    fai_te, pta_te = np.asarray(TEST["fai"], float), np.asarray(TEST["pta"], float)
    fai_tr, pta_tr = np.asarray(TRAIN["fai"], float), np.asarray(TRAIN["pta"], float)

    alpha, beta = np.polyfit(pta_tr, fai_tr, 1)
    fai_db = (fai_te - beta) / alpha
    mean = (fai_db + pta_te) / 2
    diff = fai_db - pta_te
    bias, sd = float(diff.mean()), float(diff.std())
    lo, hi = bias - 1.96 * sd, bias + 1.96 * sd

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.0))
    ax1.scatter(mean, diff, s=3, alpha=0.25, color="#2c7fb8",
                edgecolors="none", rasterized=True)
    ax1.axhline(bias, color="#b2182b", lw=1.3, label=f"bias {bias:+.2f} dB")
    for v, lab in ((hi, f"+1.96 SD {hi:+.1f}"), (lo, f"\u22121.96 SD {lo:+.1f}")):
        ax1.axhline(v, color="#b2182b", lw=0.9, ls="--", label=lab)
    ax1.axhline(0, color="0.35", lw=0.6, ls=":")
    ax1.set_xlabel("Mean of FAI (dB-equivalent) and PTA-4 (dB)")
    ax1.set_ylabel("FAI (dB-equivalent) \u2212 PTA-4 (dB)")
    ax1.set_title(f"(a) Bland-Altman, FAI mapped to dB\n"
                  f"(transfer fitted on training: FAI = {alpha:.3f}\u00b7PTA + {beta:.2f}; "
                  f"n = {len(diff):,})", fontsize=7.5)
    ax1.legend(fontsize=6.5, loc="upper right", frameon=False)

    bd = NUM["by_distance"]
    w = [r["within_db"] for r in bd]
    a = [r["agreement"] * 100 for r in bd]
    ax2.plot(w, a, "o-", color="#2c7fb8", ms=4, lw=1.3)
    for wi, ai in zip(w, a):
        ax2.annotate(f"{ai:.1f}", (wi, ai), textcoords="offset points",
                     xytext=(0, 6), ha="center", fontsize=6)
    ax2.axvspan(0, 5, color="#b2182b", alpha=0.10, hatch="///", edgecolor="#b2182b",
                linewidth=0.0)
    ax2.annotate("boundary zone", (2.6, 96.5), fontsize=6.5, color="#b2182b",
                 ha="center")
    ax2.set_xlabel("Distance from nearest Clark boundary (dB)")
    ax2.set_ylabel("Agreement (%)")
    ax2.set_title("(b) Agreement vs distance from the boundary (test set)",
                  fontsize=7.5)
    ax2.set_xticks(w); ax2.set_ylim(78, 98); ax2.grid(alpha=0.25, lw=0.4)
    fig.tight_layout()
    return save(fig, "fig2_agreement")


# ══════════════════════════════════════════════════ Figure 3 — decision curve
def figure3():
    from sklearn.linear_model import LogisticRegression

    fai_te, pta_te = np.asarray(TEST["fai"], float), np.asarray(TEST["pta"], float)
    y_te = np.asarray(TEST["y_true"])
    fai_tr, pta_tr = np.asarray(TRAIN["fai"], float), np.asarray(TRAIN["pta"], float)
    y_tr = np.asarray(TRAIN["y_true"])

    def nb(pos, out, t):
        pos, out = np.asarray(pos, bool), np.asarray(out, bool)
        return (pos & out).sum() / len(out) - (pos & ~out).sum() / len(out) * (t / (1 - t))

    ts = np.arange(0.05, 0.61, 0.01)
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
    for ax, (name, cut) in zip(axes, (("Any hearing loss (\u2265 mild)", 1),
                                      ("Moderate-or-worse loss", 2))):
        o_tr, o_te = (y_tr >= cut), (y_te >= cut)
        prev = float(o_te.mean())
        m_fai = LogisticRegression(max_iter=2000).fit(fai_tr.reshape(-1, 1), o_tr)
        m_pta = LogisticRegression(max_iter=2000).fit(pta_tr.reshape(-1, 1), o_tr)
        p_fai = m_fai.predict_proba(fai_te.reshape(-1, 1))[:, 1]
        p_pta = m_pta.predict_proba(pta_te.reshape(-1, 1))[:, 1]
        ax.plot(ts, [nb(p_fai >= t, o_te, t) for t in ts], lw=1.5,
                color="#2c7fb8", label="FAI (graded)")
        ax.plot(ts, [nb(p_pta >= t, o_te, t) for t in ts], lw=1.5, ls="--",
                color="#e08214", label="PTA-4 (crisp)")
        ax.plot(ts, [prev - (1 - prev) * (t / (1 - t)) for t in ts], lw=1.0,
                color="0.45", ls="-.", label="Treat all")
        ax.axhline(0, lw=1.0, color="black", label="Treat none")
        ax.set_xlabel("Threshold probability")
        ax.set_ylabel("Net benefit")
        ax.set_title(f"({'ab'[list(axes).index(ax)]}) {name} (prevalence {prev*100:.1f}%)",
                     fontsize=7.5)
        ax.set_xlim(0.05, 0.60); ax.set_ylim(-0.12, max(prev, 0.1) + 0.04)
        ax.grid(alpha=0.25, lw=0.4)
        # The PTA-4 curve is constant by construction: a logistic on PTA-4
        # separates this outcome with no false positives, because the outcome is
        # itself a thresholding of PTA-4. Say so, or a flat line reads as a bug.
        ax.annotate("PTA-4 flat: separates the outcome\nwith zero false positives\n"
                    "(the outcome is defined from it)",
                    xy=(0.42, prev), xytext=(0.30, prev * 0.42),
                    fontsize=5.8, color="#8c510a",
                    arrowprops=dict(arrowstyle="-", color="#8c510a", lw=0.6))
    axes[1].legend(fontsize=6.5, loc="upper right", frameon=False)
    fig.tight_layout()
    return save(fig, "fig3_decision_curve")


# ═══════════════════════════════════════════════════ Figure 4 — case panels
def figure4():
    cases = NUM["case_studies"]
    keys = ["A_BorderlineMild", "B_NoiseNotch", "C_Presbycusis", "D_Asymmetric"]
    fig, axes = plt.subplots(2, 4, figsize=(7.2, 4.2),
                             gridspec_kw={"height_ratios": [1.0, 0.95]})

    for col, key in enumerate(keys):
        c = cases[key]
        left = np.array(c["left"], float)
        ax = axes[0, col]
        ax.plot(PLOT_F, left[PLOT_IDX], "o-", color="#b2182b", ms=3.2, lw=1.1,
                label="Left" if c["right"] else "Tested ear")
        if c["right"]:
            right = np.array(c["right"], float)
            ax.plot(PLOT_F, right[PLOT_IDX], "s--", color="#2c7fb8", ms=3.2, lw=1.1,
                    label="Right")
        ax.set_xscale("log")
        ax.set_xlim(380, 11000)
        ax.set_xticks(PLOT_F)
        ax.set_xticklabels([f"{f//1000}k" if f >= 1000 else str(f) for f in PLOT_F],
                           fontsize=5.6)
        ax.invert_yaxis()
        ax.set_ylim(100, -5)
        ax.set_xlabel("Frequency (Hz)", fontsize=6.5)
        if col == 0:
            ax.set_ylabel("Threshold (dB HL)", fontsize=6.5)
        tag = key.split("_", 1)[1]
        ax.set_title(f"{'ABCD'[col]}. {tag}\nPTA-4 {c['pta4']:.1f} dB \u2192 {c['label']}",
                     fontsize=6.8)
        ax.grid(alpha=0.25, lw=0.4)
        if c["right"]:
            ax.legend(fontsize=5.4, frameon=False, loc="lower left")

        ax2 = axes[1, col]
        vals = [c["memberships"][k] for k in ORDER]
        ax2.bar(range(6), vals, color=COLOURS, alpha=0.85,
                hatch=HATCHES, edgecolor="black", linewidth=0.5)
        ax2.set_ylim(0, 1.12)
        ax2.set_xticks(range(6))
        ax2.set_xticklabels([NICE[k] for k in ORDER], rotation=55, ha="right",
                            fontsize=5.4)
        if col == 0:
            ax2.set_ylabel("Membership", fontsize=6.5)
        ax2.set_title(f"FAI {c['fai']:.1f}   shape: {c['configuration']}"
                      + (f"   asym {c['asymmetry']:.0f} dB" if c.get("asymmetry") else ""),
                      fontsize=6.5)
        ax2.grid(alpha=0.25, lw=0.4, axis="y")

    fig.suptitle("Synthetic case archetypes: thresholds, graded memberships and "
                 "derived configuration", fontsize=8, y=1.0)
    fig.tight_layout()
    return save(fig, "fig4_cases")


if __name__ == "__main__":
    print("  generating CMPB figures from committed pipeline outputs\n")
    for fn in (figure1, figure2, figure3, figure4):
        fn()
    print(f"\n  written to {FIGDIR}")
