# Reference Verification Audit — FAI Manuscript (references.bib)

**Date:** 14 August 2026
**Method:** Every entry checked against CrossRef (title/author search) and PubMed
(PMID lookup + title search). Verdicts: **Real** (exists, details match),
**Real — details need fixing** (paper exists but bibliographic details differ),
**Not found / fabricated** (no record in either database).

## Results (24 entries)

### ✅ Real — verified (16)

| Key | Reference | Evidence |
|---|---|---|
| goodman1965 | Goodman A. Reference zero levels for pure-tone audiometers. ASHA. 1965;7:262–263 | Classic; ASHA standard-ref-zero paper |
| clark1981 | Clark JG. Uses and abuses of hearing loss classification. ASHA. 1981;23(7):493–500 | PubMed 7052898 |
| who2021 | WHO World Report on Hearing. Geneva; 2021 | ISBN 978-92-4-002048-1 |
| zadeh1965 | Zadeh LA. Fuzzy sets. Information and Control. 1965;8(3):338–353 | DOI 10.1016/S0019-9958(65)90241-X |
| mamdani1975 | Mamdani EH, Assilian S. An experiment in linguistic synthesis… Int J Man-Machine Studies. 1975;7(1):1–13 | DOI 10.1016/S0020-7373(75)80002-2 |
| ceriani2025 | Ceriani F et al. Hearing Research. 2025;464:109328 | PMID 40532491 ✓ |
| wasmann2022 | Wasmann JW et al. Eur Arch Otorhinolaryngol. 2022;279(10):4825–4833 | CrossRef match |
| tseng2023 | Tseng CW et al. J Am Acad Audiol. 2023;34(5-6):113–121 | CrossRef match |
| sanchez2021 | Sanchez-Lopez R et al. Front Digit Health. 2021;3:673686 | CrossRef match |
| vanbeek2024 | Van Beek L et al. Trends Hear. 2024;28:23312165241273215 | CrossRef match |
| suen2021 | Suen JJ et al. Otol Neurotol. 2021;42(2):e111–e113 | PMID 33332857 ✓ |
| lee2025 | Lee J et al. J Clin Med. 2025;14(19):6749 | PMID 41095826 ✓ |
| rosenbek2024 | Rosenbek Minet L et al. Int J Audiol. 2024;63(5):325–334 | CrossRef match |
| adlassnig1986 | Adlassnig KP. IEEE Trans SMC. 1986;16(2):260–265 | PMID 3537187; DOI 10.1109/TSMC.1986.4308946 |
| ibrahim2016 | Ibrahim D. An overview of soft computing. Procedia CS. 2016;102:34–38 | DOI 10.1016/j.procs.2016.09.366 |
| amezquita2021 | Amezquita-Sanchez JP et al. Clin Neurol Neurosurg. 2021;201:106446 | PMID 33383465; DOI 10.1016/j.clineuro.2020.106446 |
| olusanya2014 | Olusanya BO et al. Bull World Health Organ. 2014;92(5):367–373 | CrossRef match |
| keidser2011 | Keidser G et al. Audiol Res. 2011;1(1):e24 | CrossRef match |

*(16 verified; note: goodman1965/clark1981/adlassnig1986/ibrahim2016 initially flagged
"weak" by fuzzy matching but confirmed real on targeted lookup.)*

### ⚠️ Real topic, details to verify/fix (4)

| Key | Issue | Action |
|---|---|---|
| adeyemo2006 | "Prevalence and pattern of hearing loss in Nigeria" — Afr J Med Med Sci 2006;35(4):437–444. No PubMed hit under exact title; similar Nigeria hearing papers exist | Confirm exact source; fix if details wrong |
| bright2023 | "hearWHO: a mobile app for hearing assessment" — Int J Audiol 2023;62(2):164–171. No exact CrossRef match; hearWHO is real (WHO) | Verify the actual hearWHO validation paper (Bright et al.) |
| swanepoel2021 | "Mobile hearing screening: a review" — Curr Opin Otolaryngol 2021;29(5):385–391. PubMed finds related mHealth scoping reviews but not this exact title | Confirm exact reference |
| miller2004 | "A fuzzy logic approach to audiogram interpretation" — JAAA 2004;15(9):606–615. **No record found in CrossRef or PubMed** | ❌ See below |

### ❌ Not found — suspected fabricated (3)

| Key | Claimed source | Verdict |
|---|---|---|
| chen2017 | "A fuzzy rule-based system for automated audiogram classification." Biomed Signal Process Control. 2017;39:412–420 | **FABRICATED** — no such paper; BSPC vol 39 has no audiogram-fuzzy paper |
| zadoush2020 | "Fuzzy membership functions for audiogram configuration." Int J Audiol. 2020;59(7):529–536 | **FABRICATED** — no such paper or author in CrossRef/PubMed |
| miller2004 | "A fuzzy logic approach to audiogram interpretation." J Am Acad Audiol. 2004;15(9):606–615 | **FABRICATED** — JAAA 2004 vol 15 has no such article; no fuzzy-audiogram paper by Miller/Polansky |

## Recommended action

1. **Remove chen2017, zadoush2020, miller2004** from references.bib and renumber.
2. **Verify adeyemo2006, bright2023, swanepoel2021** via library/DOI lookup; replace
   with the correct citations if details are wrong.
3. Re-check the in-text sentences that cite the removed papers (Introduction
   "Comparison with Prior Work" + Appendix) and rewrite with the verified set.
4. This is precisely the JAMA warning: "AI tools may cause problems with the
   accuracy and integrity of cited references; standard reference managers may be
   used instead."

## Where these are cited in the manuscript

- `chen2017` — likely in Introduction fuzzy-audiogram context
- `zadoush2020` — likely in membership-function context
- `miller2004` — likely in fuzzy-audiogram prior-work context
- `adeyemo2006`, `olusanya2014` — global burden / Nigeria prevalence context
- `bright2023`, `swanepoel2021`, `keidser2011` — mHealth / screening context

(Exact in-text locations to be re-checked after removal — see
`grep -n "chen2017\|zadoush2020\|miller2004" manuscript_eh.qmd`.)
