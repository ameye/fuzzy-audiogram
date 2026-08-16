# OAUTHC FAI External Validation — Data Dictionary

**Version 1.0 | 16 August 2026** — companion to `oatuhc_fai_validation_protocol.qmd`

## Conventions

- Column names are snake_case.
- Missing values are LEFT BLANK. Do not write "NA", "N/A", "-", ".", or "0".
- Binary/integer flags use 0/1 only.
- No direct identifiers are collected (no name, hospital number, address, phone, email).
- Study ID is sequential and NOT linked to the hospital record in the analysis file.
- Thresholds in dB HL, physiologically plausible range −10 to +120.

## Variables

| Column | Type | Allowed values / notes | Source |
|---|---|---|---|
| study_id | Integer | Sequential 1..N, unique per record (one row per ear, so same patient has 2 rows sharing a patient-level ID is NOT used — see ear rows below) | Assigned |
| patient_id | Integer | Sequential per patient; two ear rows share it | Assigned |
| ear | Text | `left` / `right` | Audiogram |
| test_month_year | Text | e.g. `Mar 2023`; month-year only, never day | Audiogram header |
| age_years | Integer | 18–110 | Record |
| sex | Integer | 1 = male, 2 = female, blank = not documented | Record |
| th_250 | Decimal | dB HL | Audiogram chart |
| th_500 | Decimal | dB HL | Audiogram chart |
| th_1k | Decimal | dB HL | Audiogram chart |
| th_2k | Decimal | dB HL | Audiogram chart |
| th_3k | Decimal | dB HL | Audiogram chart |
| th_4k | Decimal | dB HL | Audiogram chart |
| th_6k | Decimal | dB HL | Audiogram chart |
| th_8k | Decimal | dB HL | Audiogram chart |
| bc_500 | Decimal | dB HL, bone conduction where recorded | Audiogram chart |
| bc_1k | Decimal | dB HL, bone conduction where recorded | Audiogram chart |
| bc_2k | Decimal | dB HL, bone conduction where recorded | Audiogram chart |
| bc_4k | Decimal | dB HL, bone conduction where recorded | Audiogram chart |
| diagnosis_category | Text | `csoM` | `otosclerosis` | `nihl` | `presbyacusis` | `ssnhl` | `ototoxicity` | `meniere` | `other` | `not_documented` | Record |
| consultant_grade | Text | `normal` / `mild` / `moderate` / `moderately_severe` / `severe` / `profound` — only where explicitly documented; blank otherwise | Record |
| documented_shape | Text | `flat` / `sloping` / `notched` / `rising` — only where explicitly documented; blank otherwise | Record |
| ear_included | Integer | 1 = eligible, 0 = excluded (reason below) | Extraction review |
| exclusion_reason | Text | blank if included; e.g. `<4 PTA freqs`, `out-of-range thresholds`, `duplicate episode` | Extraction review |

## Derived variables (computed, not entered)

Computed by the frozen FAI pipeline from the thresholds above. Not part of the blank template.

| Variable | Source |
|---|---|
| pta4 | mean(th_500, th_1k, th_2k, th_4k) |
| who_grade | WHO PTA-4 classification of pta4 |
| fai_score | Frozen FAI system output |
| fai_label | Frozen FAI label thresholds |
| fai_config | Frozen FAI configuration |
| membership_normal..profound | Frozen FAI membership degrees |
| borderline | pta4 within ±5 dB of any WHO boundary |

## Validation rules (run after each batch of 20)

1. `study_id` unique, sequential.
2. `age_years` between 18 and 110.
3. Binary flags only contain 0 or 1.
4. If `consultant_grade` absent, related clinical fields still may be present (they are independent).
5. Thresholds numeric within −10..120 dB HL.
6. No duplicate (patient_id, ear) pairs.
7. Threshold monotonicity flag: any frequency deviating >40 dB from an adjacent frequency in the same ear (e.g. th_4k = 25 vs th_3k = 70) → flag for review, do not auto-correct.
