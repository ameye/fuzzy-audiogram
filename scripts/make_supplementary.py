"""Build the supplementary material the manuscript cites: Table S1 and Figure S1.

Table S1 holds the Ruspini partition parameters, which the manuscript refers to when
it says the construction is reproducible from committed code. Figure S1 shows the
temporal tracking module on serial audiograms, the illustrative-scenarios claim in
Section 3.10.

Both are derived from the fitted parameters and the live temporal module rather than
transcribed, so the supplement cannot drift from the analysis.

Run:  python3 scripts/make_supplementary.py
Writes: manuscript/supplementary/{Table_S1.csv,Figure_S1.png,Supplementary_Material.pdf}
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "manuscript" / "supplementary"
PARAMS = ROOT / "data" / "output_participant" / "params_participant.json"

ORDER = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
LABEL = {
    "normal": "Normal", "mild": "Mild", "moderate": "Moderate",
    "moderately_severe": "Moderately severe", "severe": "Severe", "profound": "Profound",
}
# calibrated FAI-to-label cut points, from the manuscript's Section 4.2
CALIB = [23.8, 48.9, 63.8, 66.4, 95.0]


def table_rows(p):
    rows = []
    for i, k in enumerate(ORDER):
        a, b, c, d = p[k]
        band = "—" if i == 0 else f"{p[ORDER[i-1]][2]:.1f}–{c:.1f}"
        width = "—" if i == 0 else f"{c - p[ORDER[i-1]][2]:.1f}"
        cross = "—" if i == 0 else f"{(p[ORDER[i-1]][2] + b) / 2:.1f}"
        cut = "—" if i == 0 else f"{CALIB[i-1]:.1f}"
        rows.append({
            "Category": LABEL[k], "P25 core (dB HL)": f"{b:.1f}", "P75 core (dB HL)": f"{c:.1f}",
            "Trapezoid [a, b, c, d]": f"[{a:.1f}, {b:.1f}, {c:.1f}, {d:.1f}]",
            "Transition band to this category (dB HL)": band,
            "Transition width (dB)": width,
            "0.5 crossover (dB HL)": cross,
            "Calibrated label cut point (dB HL)": cut,
        })
    return rows


def figure_s1(p, path):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from fuzzy_audiogram import temporal

    # a cisplatin-like course: baseline within normal limits, then progressive
    # high-frequency loss, the pattern the ASHA criteria are written for
    freq = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
    course = [
        ("Baseline", "2026-01-15", [10, 10, 10, 10, 15, 15, 15, 20]),
        ("Month 1",  "2026-02-15", [10, 10, 10, 10, 15, 20, 25, 30]),
        ("Month 2",  "2026-03-15", [10, 10, 10, 15, 25, 35, 45, 50]),
        ("Month 3",  "2026-04-15", [10, 10, 15, 20, 35, 45, 55, 60]),
        ("Month 6",  "2026-07-15", [10, 15, 15, 25, 40, 55, 65, 70]),
    ]
    series = [{"date": d, "thresholds_left": t, "thresholds_right": t}
              for _, d, t in course]

    traj = temporal.FAI_trajectory(series)
    fai = [float(v) for v in traj["fai_score"]]
    flagged = [int(dr["index"]) for dr in temporal.detect_fai_drift(fai)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    for label, _, t in course:
        ax1.plot(freq, t, marker="o", lw=1.6, label=label)
    ax1.set_xscale("log")
    ax1.set_xticks(freq)
    ax1.set_xticklabels([str(f) for f in freq])
    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Air-conduction threshold (dB HL)")
    ax1.set_title("(a) Serial audiograms")
    ax1.invert_yaxis()
    ax1.grid(alpha=0.3, ls=":")
    ax1.legend(fontsize=8, ncol=2)

    x = np.arange(len(fai))
    ax2.plot(x, fai, marker="o", lw=1.8, color="#1b5e20", label="FAI")
    if flagged:
        ax2.scatter([x[i] for i in flagged], [fai[i] for i in flagged],
                    s=110, facecolors="none", edgecolors="#b71c1c", lw=2,
                    label="ASHA shift flagged")
    ax2.set_xticks(x)
    ax2.set_xticklabels([c[0] for c in course], rotation=25, ha="right")
    ax2.set_ylabel("FAI (dB HL-equivalent)")
    ax2.set_title("(b) FAI trajectory under ototoxic drift")
    ax2.grid(alpha=0.3, ls=":")
    ax2.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=600)
    plt.close(fig)
    return fai


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = json.loads(PARAMS.read_text())
    rows = table_rows(p)

    import csv
    csv_path = OUT / "Table_S1.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  Table S1 -> {csv_path.name}  ({len(rows)} categories)")

    fig_path = OUT / "Figure_S1.png"
    fai = figure_s1(p, fig_path)
    from PIL import Image
    im = Image.open(fig_path)
    print(f"  Figure S1 -> {fig_path.name}  ({im.width} x {im.height} px)")
    print(f"    FAI trajectory: {[round(float(v), 1) for v in fai]}")

    # assemble a PDF
    import html as H
    try:
        from weasyprint import HTML
    except ImportError:
        print("  weasyprint absent; CSV and PNG written, PDF skipped")
        return
    th = "".join(f"<th>{H.escape(k)}</th>" for k in rows[0])
    tr = "".join("<tr>" + "".join(f"<td>{H.escape(str(r[k]))}</td>" for k in rows[0]) + "</tr>"
                 for r in rows)
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    @page {{ size: A4 landscape; margin: 14mm; @bottom-center {{ content: counter(page); font-size: 9pt; color:#666 }} }}
    body {{ font-family: "DejaVu Serif", Georgia, serif; font-size: 10pt; }}
    h1 {{ font-size: 15pt; }} h2 {{ font-size: 12pt; margin-top: 14pt; border-bottom: .6pt solid #999; }}
    p {{ text-align: justify; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 8pt; }}
    th, td {{ border: .5pt solid #bbb; padding: 3pt; text-align: left; }}
    th {{ background: #eee; }} img {{ width: 100%; }}</style></head><body>
    <h1>Supplementary material</h1>
    <p>Ruspini partition parameters and the temporal tracking demonstration. Generated by
    <code>scripts/make_supplementary.py</code> from the fitted parameters and the live temporal module.</p>
    <h2>Table S1. Ruspini partition parameters</h2>
    <table><tr>{th}</tr>{tr}</table>
    <p>The trapezoid [a, b, c, d] is the membership function for that category, with the core at
    [b, c] held at the empirical P25 and P75 and shoulders set so adjacent functions are
    complementary. Transition bands and 0.5 crossovers are geometric consequences of the
    parameters; the calibrated label cut points are fitted separately and are not the crossovers.</p>
    <h2>Figure S1. Temporal tracking under ototoxic drift</h2>
    <img src="{fig_path.as_uri()}"/>
    <p>Serial audiograms (a) and the resulting FAI trajectory (b). Circles mark timepoints where the
    fuzzy-adapted ASHA shift criteria flag a significant change. Illustrative only: the cohort is
    repeated cross-sectional, so no longitudinal audiometric sub-cohort exists in these data.</p>
    </body></html>"""
    pdf = OUT / "Supplementary_Material.pdf"
    HTML(string=doc).write_pdf(str(pdf))
    print(f"  Supplementary PDF -> {pdf.name}  ({pdf.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
