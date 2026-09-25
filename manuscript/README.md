# Manuscript: CMPB submission

"A Mamdani fuzzy inference framework for graded pure-tone audiometric
classification: development, validation and open-source implementation"

This directory holds the current manuscript and the chain that produces it.
`cmbp_v2/` at the repository root is ignored scratch space holding earlier
versions and working drafts; this directory is the version of record.

## Files

| File | What it is |
|---|---|
| `manuscript_v4.qmd` | The manuscript source. Main text 3,500 words, abstract 241. |
| `references_v2.bib` | Bibliography, 14 cited references, APA author-date. |
| `Manuscript_CMPB_v4.docx` | The submission build, Bookman Old Style 12 pt, justified, no first-line indent. |
| `figures/` | Four panels at 600 dpi, above the 3,543 px floor. |
| `Ruspini_Investigation_Report.pdf` | The partition construction and the calibration defect, in full. |
| `Probabilistic_Benchmark_Report.pdf` | The multi-class benchmark and the transition-width ablation. |
| `transition_sweep.json`, `bland_altman_scaled.json`, `metrics_who2021.json` | Derived values the text quotes. |

## Rebuilding

The scripts run in this order. `build_v4.py` and `verify_v4.py` need
`python-docx` and `pandoc`; everything else needs the repository's own
dependencies.

```bash
# 1. pipeline outputs — refits the memberships, calibrates the thresholds and
#    revalidates. Writes data/output_participant/.
python3 scripts/pipeline_participant.py

# 2. every number the manuscript quotes, derived rather than typed
python3 scripts/manuscript_numbers.py

# 3. the figures, read from (1) and (2)
python3 scripts/make_cmpb_figures.py

# 4. the WHO 2021 comparison arm
python3 scripts/make_who2021_ruspini.py
python3 scripts/pipeline_who2021_ruspini.py

# 5. build the DOCX and check it
python build_v4.py
python3 verify_v4.py
```

`verify_v4.py` asserts the word ceiling, the abstract length, the zero-embedded-
image rule, the absence of first person, the font, and fourteen content probes —
two of which assert that superseded claims are *absent* from the text.

## What the figures depend on

`make_cmpb_figures.py` reads `data/output_participant/metrics_participant.json`,
`manuscript_numbers.json` and the two prediction pickles. It types in no numbers.
If you change the pipeline, rebuild the figures; a figure that disagrees with the
tables is the failure mode this arrangement exists to prevent.

## Notes carried from review

Three corrections are worth knowing about, because each changed a reported value.

**The Bland-Altman comparison was dimensionally invalid.** The FAI is a
defuzzified index on a 0–100 universe, not dB HL. Earlier versions subtracted it
from PTA-4 directly and reported the result in decibels. The index is now mapped
onto the decibel scale through a transfer fitted on the training partition,
`FAI = 0.890 × PTA + 3.11`, giving bias +0.25 dB with limits −11.2 to +11.7 dB.
The previously reported +1.9 dB is withdrawn.

**The six-category scheme is Clark's, not WHO's.** WHO's own grade tables give
five categories at 20 dB steps (≤25 / 26–40 / 41–60 / 61–80 / ≥81) in both
WHO/PDH/91.1 and WHO/PDH/97.3; the 2021 revision uses seven at 15 dB steps. The
six categories at 25/40/55/70/90 dB trace to Clark and ANSI.

**Inter-aural asymmetry no longer upgrades severity.** It now drives a separate
referral output. Asymmetry is an indicator for unilateral pathology rather than
evidence that the poorer ear hears less well. The change is neutral for every
reported figure, because the single-ear validation protocol pins the asymmetry
input to zero; the test-set index is bit-identical before and after.

## Reproducibility

Every number, table and figure in this manuscript is produced by committed code.
The figures were the last exception: the earlier artwork was recovered from a
submission pack and had no generating script. `scripts/make_cmpb_figures.py`
closes that gap.
