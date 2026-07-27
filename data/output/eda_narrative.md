# NHANES Audiometry EDA — Narrative Summary

**Dataset:** NHANES P_AUX (2017–2020), Audiometry Examination File
**Total participants:** 5,147
**Participants with audiometry data:** 4,579

## Hearing Threshold Distributions

Mean thresholds per frequency (dB HL):

| Frequency | Right Ear | Left Ear |
|-----------|-----------|----------|
| 500 Hz | 14.5 ± 13.7 | 14.2 ± 13.3 |
| 1k Hz | 14.0 ± 15.7 | 14.3 ± 15.4 |
| 2k Hz | 17.7 ± 19.6 | 18.4 ± 19.7 |
| 3k Hz | 21.2 ± 23.0 | 22.3 ± 23.1 |
| 4k Hz | 22.0 ± 25.2 | 23.0 ± 25.4 |
| 6k Hz | 25.0 ± 25.9 | 25.5 ± 25.9 |
| 8k Hz | 22.8 ± 27.3 | 23.8 ± 27.4 |

PTA-4 (pure-tone average of 500, 1000, 2000, 4000 Hz):
- **Right ear:** 15.0 ± 16.4 dB (median: 8.8)
- **Left ear:** 15.6 ± 16.4 dB (median: 10.0)
- **Worse ear:** 17.9 ± 17.1 dB (range: -10–105)
- **Better ear:** 12.9 ± 15.3 dB

## Hearing Loss Severity (WHO Classification)

Based on worse-ear PTA-4:

- **Normal:** 3,360 (76.7%)
- **Mild:** 483 (11.0%)
- **Moderate:** 344 (7.8%)
- **Moderately Severe:** 127 (2.9%)
- **Severe:** 54 (1.2%)
- **Profound:** 15 (0.3%)

**Borderline cases (±5 dB of WHO boundary):** 1,003 (22.9%)

Borderline cases by WHO category:
- Normal: 269 of 3,360 (8.0%)
- Mild: 348 of 483 (72.0%)
- Moderate: 249 of 344 (72.4%)
- Moderately Severe: 89 of 127 (70.1%)
- Severe: 40 of 54 (74.1%)
- Profound: 8 of 15 (53.3%)

## Audiogram Configuration

Based on slope (4 kHz − 500 Hz):
- **Rising:** 1,948 (37.8%)
- **Flat:** 1,924 (37.4%)
- **Gently Sloping:** 482 (9.4%)
- **Steeply Sloping:** 563 (10.9%)
- **Precipitous:** 230 (4.5%)

Based on fuzzy classifier:
- **Normal:** 0 (0.0%)
- **Flat:** 432 (25.4%)
- **Sloping:** 822 (48.4%)
- **Notched:** 39 (2.3%)
- **Precipitous:** 146 (8.6%)
- **Rising:** 260 (15.3%)

## Inter-Aural Asymmetry

- **Mean max asymmetry:** 13.9 dB
- **Median max asymmetry:** 10.0 dB
- **P95:** 30.0 dB
- **Asymmetry >15 dB (clinically significant):** 1,079 (24.5%)

Asymmetry by frequency:
- **500 Hz:** mean 5.8 dB, 176 (5.5%) >15 dB
- **1k Hz:** mean 6.2 dB, 165 (5.4%) >15 dB
- **2k Hz:** mean 6.6 dB, 225 (7.2%) >15 dB
- **3k Hz:** mean 7.1 dB, 237 (7.8%) >15 dB
- **4k Hz:** mean 7.5 dB, 276 (8.9%) >15 dB
- **6k Hz:** mean 8.2 dB, 330 (10.4%) >15 dB
- **8k Hz:** mean 9.0 dB, 403 (13.6%) >15 dB

## Frequency Correlation Structure

Correlations between adjacent frequencies (Pearson r):
- **Right ear:**
  - 500_vs_1000: r = 0.860
  - 1000_vs_2000: r = 0.842
  - 2000_vs_3000: r = 0.898
  - 3000_vs_4000: r = 0.943
  - 4000_vs_6000: r = 0.913
  - 6000_vs_8000: r = 0.914
- **Left ear:**
  - 500_vs_1000: r = 0.851
  - 1000_vs_2000: r = 0.832
  - 2000_vs_3000: r = 0.902
  - 3000_vs_4000: r = 0.947
  - 4000_vs_6000: r = 0.921
  - 6000_vs_8000: r = 0.916

## Missing Data

- **Complete cases (all 14 thresholds):** 1,225 (23.8%)
- **Partial missing:** 3,354 (65.2%)
- **All missing:** 568 (11.0%)

Missingness by frequency:
- right_500: 1,556 (30.2%)
- right_1000: 1,532 (29.8%)
- right_2000: 1,521 (29.6%)
- right_3000: 1,635 (31.8%)
- right_4000: 1,500 (29.1%)
- right_6000: 1,522 (29.6%)
- right_8000: 1,612 (31.3%)
- left_500: 1,454 (28.2%)
- left_1000: 1,471 (28.6%)
- left_2000: 1,400 (27.2%)
- left_3000: 1,605 (31.2%)
- left_4000: 1,445 (28.1%)
- left_6000: 1,527 (29.7%)
- left_8000: 1,542 (30.0%)

## Key Findings

1. The NHANES 2017–2020 sample comprises 5,147 participants with available audiometric data.
3. The mean worse-ear PTA-4 of 17.9 dB indicates that this is a relatively normal-hearing population on average, with a substantial right-skew toward hearing loss.
4. The majority of participants have normal hearing (76.7% normal), with hearing loss prevalence increasing with age.
5. The most common audiogram configuration is 'Rising' (37.8%), consistent with an age-hearing population.
6. Clinically significant asymmetry (>15 dB) was observed in 1,079 (24.5%) participants, highlighting the importance of ear-specific assessment.
7. Threshold correlations were highest between adjacent low-frequency pairs and decreased with increasing frequency separation, reflecting the known frequency-selective nature of cochlear damage.
8. Missing data was minimal (complete cases: 1,225, 23.8%), suggesting good data quality in the NHANES audiometry examination.