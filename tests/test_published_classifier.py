"""Pin the deployed classifier to the published parameter set.

A reader who installs the package and calls :func:`classify_audiogram` must get
the numbers in the manuscript, not the numbers from whichever experimental
parameter set happened to be in the working tree. These tests are the guard on
that promise: the 26 dB row of Table 4 and the calibrated label cut points.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fuzzy_audiogram import core  # noqa: E402

# Manuscript Table 5.
PUBLISHED_MF_PARAMS = {
    'normal': [0.0, 0.0, 16.4, 27.8],
    'mild': [25.8, 26.3, 35.7, 43.5],
    'moderate': [41.5, 42.0, 54.3, 58.5],
    'moderately_severe': [56.5, 57.0, 67.1, 73.5],
    'severe': [71.5, 72.0, 83.6, 93.0],
    'profound': [91.0, 91.5, 106.7, 120.0],
}

# Manuscript Table 4: PTA-4, FAI score, label, Normal mu, Mild mu.
TABLE_4 = [
    (24, 11.3, 'Normal', 0.33),
    (26, 25.72, 'Mild', 0.16),
    (27, 28.9, 'Mild', 0.07),
    (28, 30.0, 'Mild', 0.00),
    (30, 30.0, 'Mild', 0.00),
]


def test_deployed_parameters_are_the_published_set():
    assert core.SEVERITY_MF_PARAMS == PUBLISHED_MF_PARAMS


def test_deployed_label_thresholds_are_calibrated():
    assert core.SEVERITY_LABEL_THRESHOLDS == [21.9, 34.6, 52.5, 70.6, 74.1]


def test_26_db_flat_ear_is_the_published_borderline_case():
    result = core.classify_audiogram([26] * 8)
    memberships = result['threshold_memberships']

    assert result['fai_score'] == pytest.approx(25.72, abs=1e-9)
    assert result['fai_label'] == 'Mild'
    assert memberships['mild'] == pytest.approx(0.400, abs=1e-9)
    assert memberships['normal'] == pytest.approx(1.8 / 11.4, abs=1e-9)


@pytest.mark.parametrize('pta, expected_fai, expected_label, normal_mu', TABLE_4)
def test_table_4_rows_reproduce(pta, expected_fai, expected_label, normal_mu):
    result = core.classify_audiogram([pta] * 8)

    assert result['fai_score'] == pytest.approx(expected_fai, abs=0.06)
    assert result['fai_label'] == expected_label
    assert result['threshold_memberships']['normal'] == pytest.approx(normal_mu, abs=0.005)
    assert np.isfinite(result['fai_score'])
