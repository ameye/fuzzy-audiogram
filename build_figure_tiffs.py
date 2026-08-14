#!/usr/bin/env python3
"""Convert the 6 manuscript figures to individual TIFF files for Ear and Hearing
submission (LWW requires TIFF/EPS, >=300 dpi). RGBA -> RGB (flatten on white),
LZW compression, dpi tag embedded. Files named Figure_1.tiff ... Figure_6.tiff
in eh_submission/figures/.
"""
from PIL import Image
from pathlib import Path

ROOT = Path("/opt/data/fuzzy-audiogram")
SRC = {
    1: "fig1_membership_functions.png",
    2: "fig2_fis_architecture.png",
    3: "fig3_fai_agreement.png",
    4: "fig4_clinical_cases.png",
    5: "fig_eda_config_dist.png",
    6: "fig7_longitudinal.png",
}
OUT = ROOT / "eh_submission" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

CAPTIONS = {
    1: "Overlapping trapezoidal membership functions for six hearing loss severity "
       "categories, with NHANES threshold density overlay. Population-optimised "
       "boundaries sit about 8 dB to the right of the classic WHO thresholds.",
    2: "Schematic of the Mamdani fuzzy inference system architecture: "
       "frequency-specific threshold inputs to fuzzification via membership "
       "functions to a 48-rule inference engine to centroid defuzzification, "
       "yielding the FAI, configuration vector, and asymmetry index.",
    3: "(a) Bland-Altman plot showing agreement between FAI and PTA-4 reference on "
       "the held-out test set. (b) Classification agreement as a function of "
       "distance from the nearest WHO severity boundary: the FAI matches the crisp "
       "grade on 94.2% of clear cases (\u22656 dB from a boundary) and returns graded "
       "membership on 56.3% of borderline cases (\u00b15 dB).",
    4: "Clinical case panels: four representative audiograms (A borderline, "
       "B noise notch, C presbycusis, D asymmetric) showing PTA vs FAI labels, "
       "membership bar plots, and configuration vectors. Coloured background "
       "bands indicate WHO severity categories.",
    5: "Configuration distribution in the NHANES cohort (slope = 4 kHz \u2212 500 Hz): "
       "predominantly flat and gently sloping patterns; the fuzzy shape rules "
       "emit a six-category membership vector.",
    6: "Longitudinal FAI trajectories for three clinical scenarios over 4\u20138 "
       "years. FAI shows smoother, more physiologically plausible progression "
       "than the stepwise PTA grade changes.",
}

for num, fname in SRC.items():
    src = ROOT / "figures" / fname
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    dpi = src_dpi = im2.info.get("dpi", (300, 300)) if (im2 := Image.open(src)) else (300, 300)
    # use native dpi if present, else 300
    native = Image.open(src).info.get("dpi", (300, 300))
    dpi = tuple(int(round(x)) if x else 300 for x in native)
    out = OUT / f"Figure_{num}.tiff"
    im.save(out, format="TIFF", compression="tiff_lzw", dpi=dpi)
    w_in = im.size[0] / dpi[0]
    print(f"Figure_{num}.tiff: {im.size} {im.mode} dpi={dpi} width={w_in:.2f}in")

# captions file
cap_path = OUT / "figure_captions.txt"
with open(cap_path, "w", encoding="utf-8") as f:
    for num in sorted(CAPTIONS):
        f.write(f"Figure {num}. {CAPTIONS[num]}\n\n")
print("wrote", cap_path)
