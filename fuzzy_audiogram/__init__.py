"""
fuzzy_audiogram — Fuzzy Logic Framework for Audiogram Interpretation
=====================================================================
A fuzzy inference system (FIS) for hearing loss classification
that preserves diagnostic gradation lost to crisp dB thresholds.

Provides continuous Fuzzy Audiometric Index (FAI) scoring,
configuration classification, NHANES data integration,
temporal tracking, and validation against crisp/machine-learning models.
"""

__version__ = "0.2.0"
__author__ = "Sanyaolu Ameye"

from .core import (
    create_severity_universe,
    create_slope_universe,
    create_asymmetry_universe,
    build_audiogram_fis,
    compute_audiogram_features,
    classify_audiogram,
    compare_fuzzy_vs_crisp,
    demo_cases,
)

from .data import (
    load_nhanes,
    extract_audiometry,
    nhanes_demo,
)

from .viz import (
    plot_severity_membership,
    plot_slope_membership,
    plot_asymmetry_membership,
    plot_notch_membership,
    plot_audiogram_with_fuzzy,
    plot_fai_vs_pta_comparison,
    plot_nhanes_distribution,
)

from .validate import (
    crisp_classify,
    compute_metrics,
    train_xgboost,
    train_random_forest,
    run_validation,
)

from .temporal import (
    FAI_trajectory,
    detect_fai_drift,
    ototoxicity_monitor,
)

__all__ = [
    # core
    "create_severity_universe",
    "create_slope_universe",
    "create_asymmetry_universe",
    "build_audiogram_fis",
    "compute_audiogram_features",
    "classify_audiogram",
    "compare_fuzzy_vs_crisp",
    "demo_cases",
    # data
    "load_nhanes",
    "extract_audiometry",
    "nhanes_demo",
    # viz
    "plot_severity_membership",
    "plot_slope_membership",
    "plot_asymmetry_membership",
    "plot_notch_membership",
    "plot_audiogram_with_fuzzy",
    "plot_fai_vs_pta_comparison",
    "plot_nhanes_distribution",
    # validate
    "crisp_classify",
    "compute_metrics",
    "train_xgboost",
    "train_random_forest",
    "run_validation",
    # temporal
    "FAI_trajectory",
    "detect_fai_drift",
    "ototoxicity_monitor",
]
