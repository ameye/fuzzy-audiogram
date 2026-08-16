# FAI Pipeline Extension — Results

**Date:** 2026-08-16 | **Repo:** ameye/fuzzy-audiogram


## Leg A — External Validation (P_AUX 2017-2020)

- External dataset: NHANES P_AUX 2017-2020 (6-19y + >=70y) (n=7944 clean ears, 5147 participants)

- **Full external set**: n=7944, κ=0.941, overall=94.7%, borderline=77.6%, clear=98.4%, MAE=5.48 dB, ρ=0.783

- **Children 6-19**: n=5845, κ=0.981, overall=99.8%, borderline=94.1%, clear=100.0%, MAE=5.24 dB, ρ=0.385

- **Adults ≥70**: n=2099, κ=0.896, overall=80.3%, borderline=75.9%, clear=87.1%, MAE=6.15 dB, ρ=0.923


## Leg B — Comparator Suite (multiclass, WHO grade direct)

| Model | κ | Overall | Borderline | Clear |
|---|---|---|---|---|

| Multinomial LR | 0.971 | 99.2% | 96.6% | 99.8% |

| kNN-15 | 0.97 | 98.2% | 90.4% | 100.0% |

| MLP | 0.909 | 96.2% | 83.3% | 99.2% |

| XGBoost (classifier) | 0.988 | 99.3% | 96.4% | 99.9% |

| Random Forest (classifier) | 0.979 | 98.7% | 93.3% | 99.9% |

| FAI (fuzzy, participant pipeline) | 0.931 | 94.7% | 79.8% | 98.1% |


## Leg C — Sensitivity


### Overlap sweep (seed 42)

| Overlap | κ | Overall | Borderline | Clear |
|---|---|---|---|---|

| 1.0 dB | 0.857 | 88.5% | 62.1% | 94.5% |

| 2.0 dB | 0.931 | 94.7% | 79.8% | 98.1% |

| 3.0 dB | 0.934 | 95.1% | 80.8% | 98.4% |

| 5.0 dB | 0.905 | 93.2% | 71.7% | 98.1% |


### Seed sweep

| Seed | κ | Overall | Borderline | Clear |
|---|---|---|---|---|

| 7 | 0.918 | 95.4% | 81.4% | 98.5% |

| 42 | 0.931 | 94.7% | 79.8% | 98.1% |

| 123 | 0.921 | 94.5% | 79.8% | 97.8% |

| 2024 | 0.922 | 94.7% | 81.1% | 97.8% |

| 999 | 0.924 | 94.8% | 80.2% | 98.2% |


Seed κ: mean 0.923 ± 0.004 (range 0.918–0.931)


### Age-decade subgroups (participant test, seed 42)

| Decade | n | κ | Overall | Borderline | Clear |
|---|---|---|---|---|---|

| 20s | 867 | 0.932 | 99.5% | 95.8% | 99.6% |

| 30s | 830 | 0.947 | 98.7% | 87.5% | 99.4% |

| 40s | 735 | 0.939 | 96.0% | 81.4% | 98.4% |

| 50s | 706 | 0.94 | 92.5% | 80.4% | 97.1% |

| 60s | 774 | 0.898 | 85.5% | 76.9% | 93.2% |
