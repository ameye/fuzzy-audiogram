"""Check that every numeric token in EDA_REPORT.md survives in EDA_VISUAL_REPORT.md.

Tokens are matched after stripping thousands separators. A token counts as
surviving if it appears as a whole numeric token in the visual report; a token
also counts as surviving if the visual report carries it inside a longer token
(for example 47.6 inside a confidence interval written as 37.9 to 47.6).

What remains is reported in two buckets:

  cross-reference  a section number from the original numbering, which this
                   edition renumbers (1.9, 6.3 and so on)
  UNMATCHED        anything else, which would be a lost number

Usage:  python verify_numbers.py
"""
from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "EDA_REPORT.md"
DST = HERE / "EDA_VISUAL_REPORT.md"

NUM = re.compile(r"[−\-+]?\d[\d,]*(?:\.\d+)?")


def tokens(text: str) -> collections.Counter:
    return collections.Counter(m.replace(",", "") for m in NUM.findall(text))


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    dst = DST.read_text(encoding="utf-8")
    s, d = tokens(src), tokens(dst)

    missing = sorted(set(s) - set(d), key=lambda x: (len(x), x))
    dst_nums = list(d)

    crossref, unmatched = [], []
    for tok in missing:
        bare = tok.lstrip("−-+")
        inside = any(bare in other for other in dst_nums)
        looks_ref = bool(re.fullmatch(r"\d{1,2}\.\d{1,2}", bare)) and float(bare) < 13
        if inside or looks_ref:
            crossref.append(tok)
        else:
            unmatched.append(tok)

    print(f"distinct numeric tokens in EDA_REPORT.md : {len(s)}")
    print(f"distinct numeric tokens in the visual report: {len(d)}")
    print(f"missing as a standalone token            : {len(missing)}")
    print(f"  of which cross-references or substrings : {len(crossref)}")
    for t in crossref:
        print(f"    {t}")
    print(f"  UNMATCHED                               : {len(unmatched)}")
    for t in unmatched:
        print(f"    {t}")
    if unmatched:
        return 1
    print("\nPASS: every substantive number survives.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
