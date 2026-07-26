# Meeting Brief: Fuzzy Audiogram Project
## Dr Sanyaolu Ameye × Dr Adebola Adeyemo
### Monday 27 July 2026, 11:00 PM Riyadh (UTC+3)

---

## 1. Project Overview

**Title:** A Fuzzy Logic Framework for Sensorineural Hearing Loss Classification

**What it does:** A Mamdani-type Fuzzy Inference System (FIS) that maps pure-tone audiogram thresholds into a continuous **Fuzzy Audiometric Index (FAI)** — preserving the gradation that conventional crisp WHO thresholds discard.

**Data source:** NHANES 2017–2020 (n = 5,147 participants, 80/20 train/test split)

**Status:** Pre-submission — manuscript drafted, code open-sourced, validation complete on NHANES held-out test set.

---

## 2. Key Results

| Metric | Value |
|--------|-------|
| FIS Rule Base | 48 Mamdani-type rules (4 groups) |
| Weighted κ vs. PTA-4 | 0.89 (excellent agreement) |
| Borderline accuracy (±5 dB) | **91.2%** — vs. **68.4%** for PTA-4 (p < 0.01) |
| Configuration classification | 89.4% accuracy (6 shapes, κ = 0.86) |
| Sub-threshold progression detected | 28% of longitudinal cases |
| Spearman ρ vs. PTA-4 | 0.96 |

**Clinical advantage:** At the 25/26 dB boundary, the FIS assigns graded membership (Normal μ = 0.40, Mild μ = 1.00) rather than a forced binary label.

---

## 3. Current Assets

| Asset | Location |
|-------|----------|
| Source code & pipeline | github.com/ameye/fuzzy-audiogram |
| Manuscript (PDF/DOCX) | Ready for submission |
| Comprehensive technical report | 12 sections, all analyses documented |
| All figures | 7 manuscript + 9 EDA figures |
| NHANES classification results | 4,475 participants classified (CSV) |

---

## 4. Proposed UCH Ibadan Collaboration

**What UCH can provide:**

- **Clinical audiogram dataset** (500+ ears) — real-world Nigerian population with diverse configurations
- **ENT expertise** — rule base refinement, clinical interpretation
- **Validation cohort** — Menière's, otosclerosis, CSOM patterns underrepresented in NHANES

**What we offer in return:**

- Co-authorship on manuscript (validation section)
- Joint development of web-based FAI Calculator for clinical use
- CV-based audiogram extraction tool (currently in planning)
- Open-source credit and academic collaboration

**Timeline:**

- Phase 1 (Aug 2026): Collect audiograms → run through existing FIS → compare with ENT clinical grading
- Phase 2 (Sept 2026): Publish validation results — submit manuscript to *Ear & Hearing* or *Int J Audiology*
- Phase 3 (Oct 2026): Deploy FAI Calculator + CV scanner at UCH (pilot)

---

## 5. Talking Points

1. **"The FAI doesn't replace clinical judgment — it augments it."** The system outputs interpretable membership degrees, not black-box probabilities. Every rule can be inspected.

2. **"The borderline problem is real — 39% of NHANES ears fall within ±5 dB of a WHO boundary."** This is where the fuzzy system adds the most value.

3. **"UCH data would strengthen the manuscript significantly."** The current study uses only NHANES (US population). Nigerian clinical data would demonstrate generalisability across populations and healthcare settings.

4. **"We can build an FAI Calculator together."** A web-based tool where ENT surgeons can enter thresholds and get instant FAI scores + configuration vectors + longitudinal tracking.

---

## 6. Links

- **GitHub:** https://github.com/ameye/fuzzy-audiogram
- **Comprehensive report:** `comprehensive_report.pdf` (3.8 MB)
- **Manuscript:** `manuscript.pdf` (2.0 MB)
- **Contact:** sanyaameye@hotmail.com

---

*Brief prepared by Hermes Agent — 27 July 2026*
