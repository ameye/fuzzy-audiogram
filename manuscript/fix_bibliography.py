#!/usr/bin/env python3
"""Correct the bibliographic attributions flagged in review.

Findings that drive these edits, all verified against primary sources:

  * The six-category severity scheme at 25/40/55/70/90 dB is Clark/ANSI, not
    WHO. WHO's own tables give five grades at 20 dB steps (<=25 / 26-40 /
    41-60 / 61-80 / >=81) in both WHO/PDH/91.1 (1991) and WHO/PDH/97.3 (1997).
  * The bib entry dated 1997 carried the 1991 report's title. The real 1997
    document is the First Informal Consultation report, WHO/PDH/97.3.
  * Clark (1981) codified the classic three-frequency average (500/1000/2000),
    not the four-frequency window that WHO later adopted for grading.
  * Suen (2021) defined asymmetry from pure-tone averages (AAO-HNS, >15 dB) and
    from contiguous frequencies (VA), not from a maximum single-frequency gap.
"""
import re, sys, shutil
from pathlib import Path

BIB = Path("/opt/data/fuzzy-audiogram/cmbp_v2/references_v2.bib")
shutil.copy(BIB, BIB.with_suffix(".bib.pre_fix"))
s = BIB.read_text(encoding="utf-8")

# ---- 1. correct the mis-dated WHO entry, and add the 1991 primary report
old_who = re.search(r"@book\{who1997,.*?\n\}", s, re.S).group(0)
new_who = """@book{who1997,
  title     = {Future programme developments for prevention of deafness and hearing impairment: report of the first informal consultation, Geneva, 23--24 January 1997},
  author    = {{World Health Organization}},
  year      = {1997},
  address   = {Geneva},
  publisher = {World Health Organization},
  note      = {Document WHO/PDH/97.3}
}

@book{who1991,
  title     = {Report of the informal working group on prevention of deafness and hearing impairment programme planning, Geneva, 18--21 June 1991},
  author    = {{World Health Organization}},
  year      = {1991},
  address   = {Geneva},
  publisher = {World Health Organization},
  note      = {Document WHO/PDH/91.1}
}"""
s = s.replace(old_who, new_who, 1)

# ---- 2. Clark: note the three-frequency average
s = s.replace(
    "  pages={493--500},\n  year={1981}\n}",
    "  pages={493--500},\n  year={1981},\n"
    "  note={Defines the classic categorical severity tiers on the three-frequency\n"
    "        average (500, 1000, 2000 Hz); the four-frequency window including\n"
    "        4000 Hz was adopted later by WHO for grading}\n}",
    1)

# ---- 3. Suen: record the criteria actually used
s = s.replace(
    "  pmid={33332857}\n}",
    "  pmid={33332857},\n"
    "  note={Applies two criteria: AAO-HNS asymmetry as a pure-tone-average\n"
    "        difference greater than 15 dB, and a Veterans Affairs criterion of\n"
    "        >=20 dB across two contiguous frequencies or >=10 dB across three.\n"
    "        Note that no standard audiometric criterion for asymmetry exists}\n}",
    1)

BIB.write_text(s, encoding="utf-8")

keys = sorted(re.findall(r"@\w+\{([^,]+),", s))
print(f"  bib keys now ({len(keys)}): {', '.join(keys)}")

checks = [
    ("who1997 retitled", "first informal consultation"),
    ("who1991 added", "@book{who1991,"),
    ("Clark note", "three-frequency"),
    ("Suen note", "no standard audiometric criterion"),
    ("old working-group title no longer on who1997",
     "informal working group on prevention of deafness and hearing impairment programme planning},\n  author"),
]
ok = True
for label, probe in checks:
    present = probe in s
    want_absent = label.startswith("old working-group")
    good = (not present) if want_absent else present
    if not good:
        ok = False
    print(f"  {'OK  ' if good else 'FAIL'}  {label}")
sys.exit(0 if ok else 1)
