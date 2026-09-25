#!/usr/bin/env python3
"""Final verification of the CMPB v4 manuscript."""
import re
from docx import Document

import os
# Resolve beside this file. It previously pointed at cmbp_v2/, the superseded
# scratch dir, so it silently verified a stale document.
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Manuscript_CMPB_v4.docx")
d = Document(PATH)
paras = [p.text.strip() for p in d.paragraphs if p.text.strip()]
# Table cells carry several asserted values; without them those probes cannot pass.
for _t in d.tables:
    for _r in _t.rows:
        for _c in _r.cells:
            if _c.text.strip():
                paras.append(_c.text.strip())


def wc(t):
    return len([w for w in t.split() if re.search(r"[A-Za-z0-9]", w)])


a = next(i for i, p in enumerate(paras) if re.match(r"^\d+\tIntroduction", p))
BACK_MATTER = ("Highlights", "CRediT", "Acknowledgements")
b = next(i for i, p in enumerate(paras)
         if len(p) < 40 and any(k in p for k in BACK_MATTER))
HEAD = re.compile(r"^\d+(\.\d+)*\t")
body = [p for p in paras[a + 1:b] if not HEAD.match(p)]
joined = " ".join(body)

ab = next(j for j, p in enumerate(paras) if p.startswith("Background and Objective"))
kw = next(j for j, p in enumerate(paras) if p.startswith("Keywords"))
refs = [p for p in paras if re.match(r"^\[\d+\]", p)]
figs = sorted(set(re.findall(r"Figure (\d)", joined)))

main = wc(joined)
abst = wc(" ".join(paras[ab:kw]))

print("=" * 62)
print("  CMPB v4 -- final verification")
print("=" * 62)
print(f"  main text        {main} / 3500        {'PASS' if main <= 3500 else 'OVER by ' + str(main - 3500)}")
print(f"  abstract         {abst} / 350         {'PASS' if abst <= 350 else 'OVER'}")
print(f"  references       {len(refs)} / 50")
print(f"  figures cited    {figs}")
print(f"  embedded images  {len(d.inline_shapes)}   (must be 0; artwork ships separately)")
print(f"  first-person     {len(re.findall(r'\b(?:We|we|our|Our|I|my)\b', joined))}   (must be 0)")
print(f"  font             {d.styles['Normal'].font.name} "
      f"{d.styles['Normal'].font.size.pt:g}pt")

probes = [
    ("Ruspini partition",            "Ruspini partition"),
    ("sum to one",                   "sum to exactly 1"),
    ("membership argmax reported",   "kappa 0.9453"),
    ("transition width floor",       "minimum transition width"),
    ("probabilistic comparators",    "proportional-odds ordinal logistic"),
    ("Brier score reported",         "Brier score of 0.0482"),
    ("no stale 4.6 numbers",        "0.0474", True),
    ("deterministic label",          "deterministic thresholding"),
    ("transition ablation",          "Transition-Width Ablation"),
    ("ablation CI",                  "−0.0014 to +0.0058"),
    ("per-class table",              "Macro-averaged sensitivity 0.891"),
    ("decision curve",               "net benefit"),
    ("Clark for the six cut-offs",    "Clark PTA-4 grade"),
    ("WHO 1997 cited for grades",    "five categories at 20 dB steps"),
    ("WHO 2021 difference",          "normal boundary to 20 dB"),
    ("single-ear protocol",          "single-ear protocol"),
    ("no longitudinal cohort",       "no longitudinal audiometric sub-cohort"),
    ("open-source repo in data statement", "github.com/ameye/fuzzy-audiogram"),
    ("corrected kappa",              "kappa 0.946"),
    ("corrected borderline",         "86.3%"),
    ("no stale borderline",          "85.1%", True),
    ("no stale BA caption",          "+1.9 dB", True),
    ("Clark three-frequency basis",  "three-frequency average"),
    ("four-frequency credited to WHO", "four-frequency window that WHO later adopted"),
    ("Fig 2 caption states transfer", "0.890"),
    ("Fig 2 caption says Clark",     "nearest Clark severity boundary"),
    ("sweep best setting",           "best-performing floor"),
    ("GB now beats the FAI",         "0.9832 against the memberships"),
    ("ablation floor effect small",  "non-significant gain"),
    ("no stale GB kappa",            "0.9177", True),
    ("no stale ablation CI",         "+0.0190", True),
    ("no stale cohort",              "19,568", True),
    ("Table 1 Wilson intervals",     "0.757"),
    ("WHO/PDH/91.1 code",            "WHO/PDH/91.1"),
    ("Suen: United States cased",    "United States"),
    ("no [2,3] grouping",            "[2,3]", True),
    ("no mixed-loss naming",         "mixed-loss", True),
    ("abstract rule count = 42",     "42-rule Mamdani"),
    ("no 47-rule claim",            "47-rule", True),
    ("four-group split stated",      "A further 12 rules"),
    ("no stale 0.95 claim",          "0.95 against the WHO"),
]
print("\n  content probes:")
bad = 0
for _p in probes:
    label, probe = _p[0], _p[1]
    absent = len(_p) > 2 and bool(_p[2])
    hit = probe.lower() in joined.lower() or probe.lower() in " ".join(paras).lower()
    if absent or probe == "0.95 against the WHO":
        hit = not hit          # these must be ABSENT
        label += " (must be absent)"
    if not hit:
        bad += 1
    print(f"    {'OK  ' if hit else 'FAIL'}  {label}")

print(f"\n  reference list ({len(refs)}):")
for p in refs:
    print("   ", p[:88])
print(f"\n  probes failed: {bad}")
