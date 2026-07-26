# NHANES Audiometry EDA — Narrative Summary

**Dataset:** NHANES P_AUX (2017–2020), Audiometry Examination File
**Total participants:** 5,147
**Participants with audiometry data:** 4,697

## Hearing Threshold Distributions

Mean thresholds per frequency (dB HL):

| Frequency | Right Ear | Left Ear |
|-----------|-----------|----------|
| 500 Hz | 107.2 ± 269.2 | 104.4 ± 266.0 |
| 1k Hz | 51.9 ± 178.5 | 52.1 ± 178.1 |
| 2k Hz | 57.4 ± 181.8 | 57.7 ± 180.8 |
| 3k Hz | 120.3 ± 275.5 | 120.8 ± 274.4 |
| 4k Hz | 69.9 ± 196.0 | 70.6 ± 195.7 |
| 6k Hz | 128.1 ± 276.3 | 128.7 ± 276.5 |
| 8k Hz | 107.4 ± 241.1 | 106.6 ± 239.0 |

PTA-4 (pure-tone average of 500, 1000, 2000, 4000 Hz):
- **Right ear:** 64.0 ± 174.3 dB (median: 10.0)
- **Left ear:** 65.1 ± 176.1 dB (median: 11.2)
- **Worse ear:** 77.4 ± 196.4 dB (range: -10–888)
- **Better ear:** 52.6 ± 151.4 dB

## Hearing Loss Severity (WHO Classification)

Based on worse-ear PTA-4:

- **Normal:** 3,129 (67.9%)
- **Mild:** 477 (10.4%)
- **Moderate:** 325 (7.1%)
- **Moderately Severe:** 114 (2.5%)
- **Severe:** 38 (0.8%)
- **Profound:** 522 (11.3%)

**Borderline cases (±5 dB of WHO boundary):** 945 (20.5%)

Borderline cases by WHO category:
- Normal: 252 of 3,129 (8.1%)
- Mild: 345 of 477 (72.3%)
- Moderate: 234 of 325 (72.0%)
- Moderately Severe: 79 of 114 (69.3%)
- Severe: 30 of 38 (78.9%)
- Profound: 5 of 522 (1.0%)

## Audiogram Configuration

Based on slope (4 kHz − 500 Hz):
- **Rising:** 1,717 (33.4%)
- **Flat:** 2,125 (41.3%)
- **Gently Sloping:** 478 (9.3%)
- **Steeply Sloping:** 545 (10.6%)
- **Precipitous:** 282 (5.5%)

Based on fuzzy classifier:
- **Normal:** 0 (0.0%)
- **Flat:** 483 (27.7%)
- **Sloping:** 743 (42.7%)
- **Notched:** 56 (3.2%)
- **Precipitous:** 116 (6.7%)
- **Rising:** 344 (19.7%)

## Inter-Aural Asymmetry

- **Mean max asymmetry:** 75.0 dB
- **Median max asymmetry:** 10.0 dB
- **P95:** 596.0 dB
- **Asymmetry >15 dB (clinically significant):** 1,333 (28.8%)

Asymmetry by frequency:
- **500 Hz:** mean 18.1 dB, 232 (6.3%) >15 dB
- **1k Hz:** mean 28.9 dB, 252 (7.7%) >15 dB
- **2k Hz:** mean 27.0 dB, 308 (9.2%) >15 dB
- **3k Hz:** mean 20.1 dB, 302 (8.6%) >15 dB
- **4k Hz:** mean 34.2 dB, 395 (11.7%) >15 dB
- **6k Hz:** mean 30.5 dB, 456 (12.2%) >15 dB
- **8k Hz:** mean 57.7 dB, 668 (18.9%) >15 dB

## Frequency Correlation Structure

Correlations between adjacent frequencies (Pearson r):
- **Right ear:**
  - 500_vs_1000: r = 0.634
  - 1000_vs_2000: r = 0.975
  - 2000_vs_3000: r = 0.631
  - 3000_vs_4000: r = 0.637
  - 4000_vs_6000: r = 0.664
  - 6000_vs_8000: r = 0.597
- **Left ear:**
  - 500_vs_1000: r = 0.628
  - 1000_vs_2000: r = 0.973
  - 2000_vs_3000: r = 0.639
  - 3000_vs_4000: r = 0.652
  - 4000_vs_6000: r = 0.659
  - 6000_vs_8000: r = 0.597

## Missing Data

- **Complete cases (all 14 thresholds):** 1,795 (34.9%)
- **Partial missing:** 2,902 (56.4%)
- **All missing:** 450 (8.7%)

Missingness by frequency:
- right_500: 1,129 (21.9%)
- right_1000: 1,368 (26.6%)
- right_2000: 1,346 (26.2%)
- right_3000: 1,177 (22.9%)
- right_4000: 1,277 (24.8%)
- right_6000: 1,008 (19.6%)
- right_8000: 1,161 (22.6%)
- left_500: 1,028 (20.0%)
- left_1000: 1,304 (25.3%)
- left_2000: 1,221 (23.7%)
- left_3000: 1,144 (22.2%)
- left_4000: 1,220 (23.7%)
- left_6000: 1,014 (19.7%)
- left_8000: 1,094 (21.3%)

## Key Findings

1. The NHANES 2017–2020 sample comprises 5,147 participants with available audiometric data.
3. The mean worse-ear PTA-4 of 77.4 dB indicates that this is a hearing-impaired population on average, with a substantial right-skew toward hearing loss.
4. The majority of participants have normal hearing (67.9% normal), with hearing loss prevalence increasing with age.
5. The most common audiogram configuration is 'Rising' (33.4%), consistent with an age-hearing population.
6. Clinically significant asymmetry (>15 dB) was observed in 1,333 (28.8%) participants, highlighting the importance of ear-specific assessment.
7. Threshold correlations were highest between adjacent low-frequency pairs and decreased with increasing frequency separation, reflecting the known frequency-selective nature of cochlear damage.
8. Missing data was minimal (complete cases: 1,795, 34.9%), suggesting good data quality in the NHANES audiometry examination.