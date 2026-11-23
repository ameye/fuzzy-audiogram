"""Pin the deployed classifier to the published (Ruspini) configuration.

A reader who installs the package and calls :func:`classify_audiogram` must get
the numbers in the manuscript. These tests are the guard on that promise: the
membership functions must be the Ruspini partition committed to
``data/output_participant/metrics_participant.json``, the partition must hold at
0 failures, and the 24-30 dB rows of Table 4 must reproduce.

The superseded published set (``data/output/params_combined.json``) reproduced
the old Table 4 but was not a partition, so it cannot pass the partition test.
That is the whole point of the change: the partition claim is now checked
against the constants the package actually ships.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fuzzy_audiogram import core  # noqa: E402
from fuzzy_audiogram.ruspini import partition_sum, verify  # noqa: E402

METRICS = ROOT / "data" / "output_participant" / "metrics_participant.json"

# Manuscript Table 5 / core.SEVERITY_MF_PARAMS.
PUBLISHED_MF_PARAMS = {
    'normal': [-0.5, 0.0, 16.4, 30.0],
    'mild': [16.4, 30.0, 35.4, 45.4],
    'moderate': [35.4, 45.4, 52.1, 62.1],
    'moderately_severe': [52.1, 62.1, 66.1, 76.1],
    'severe': [66.1, 76.1, 85.0, 95.9],
    'profound': [85.0, 95.9, 120.0, 120.5],
}

# Manuscript Table 4: PTA-4, FAI score, label, Normal mu, Mild mu.
TABLE_4 = [
    (24, 22.37, 'Normal', 0.44),
    (26, 24.99, 'Mild', 0.29),
    (27, 26.26, 'Mild', 0.22),
    (28, 27.51, 'Mild', 0.15),
    (30, 30.00, 'Mild', 0.00),
]


def test_deployed_parameters_are_the_published_partition():
    assert core.SEVERITY_MF_PARAMS == PUBLISHED_MF_PARAMS


def test_deployed_parameters_match_the_committed_run():
    committed = json.loads(METRICS.read_text(encoding="utf-8"))
    assert core.SEVERITY_MF_PARAMS == committed["mf_params"]
    assert core.SEVERITY_LABEL_THRESHOLDS == committed["label_thresholds"]


def test_deployed_label_thresholds_are_calibrated():
    assert core.SEVERITY_LABEL_THRESHOLDS == [24.6, 48.2, 57.3, 74.0, 85.8]


def test_deployed_memberships_are_a_ruspini_partition():
    """The claim the manuscript makes, checked on the deployed constants."""
    rep = verify(core.SEVERITY_MF_PARAMS)
    assert rep["is_partition"], rep
    assert rep["n_offending"] == 0, rep
    assert rep["n_uncovered"] == 0, rep
    assert rep["points_checked"] == 1201, rep
    assert rep["max_deviation"] <= 1e-9, rep


def test_sum_to_one_at_the_endpoints_and_in_the_gap():
    for x in (0.0, 25.8, 26.0, 60.0, 120.0):
        assert partition_sum(core.SEVERITY_MF_PARAMS, x) == pytest.approx(1.0, abs=1e-9)


def test_26_db_flat_ear_is_the_published_borderline_case():
    result = core.classify_audiogram([26] * 8)
    memberships = result['threshold_memberships']

    assert result['fai_score'] == pytest.approx(24.99, abs=0.01)
    assert result['fai_label'] == 'Mild'
    assert memberships['mild'] == pytest.approx(0.706, abs=0.001)
    assert memberships['normal'] == pytest.approx(0.294, abs=0.001)
    assert sum(memberships.values()) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize('pta, expected_fai, expected_label, normal_mu', TABLE_4)
def test_table_4_rows_reproduce(pta, expected_fai, expected_label, normal_mu):
    result = core.classify_audiogram([pta] * 8)

    assert result['fai_score'] == pytest.approx(expected_fai, abs=0.02)
    assert result['fai_label'] == expected_label
    assert result['threshold_memberships']['normal'] == pytest.approx(normal_mu, abs=0.006)
    assert sum(result['threshold_memberships'].values()) == pytest.approx(1.0, abs=1e-9)


def test_rule_base_is_42_rules_in_four_groups():
    """The count in the manuscript and the deck must be the count the code builds."""
    system, *_ = core.build_audiogram_fis(single_ear=True)
    rules = list(system.rules)
    assert len(rules) == 42

    # 12 severity + 4 contour rules both target severity; 14 target shape;
    # 12 target referral.
    by_consequent = {}
    for rule in rules:
        for weighted in rule.consequent:
            label = weighted.term.parent.label
            by_consequent[label] = by_consequent.get(label, 0) + 1
    assert by_consequent == {'severity': 16, 'audiogram_shape': 14, 'referral': 12}

    bilateral, *_ = core.build_audiogram_fis(single_ear=False)
    assert len(list(bilateral.rules)) == 42


def test_superseded_set_is_not_a_partition():
    """Regression guard: the old params must keep failing, so the change is real."""
    legacy = json.loads(
        (ROOT / "data" / "output" / "params_combined.json").read_text(encoding="utf-8")
    )
    rep = verify(legacy)
    assert not rep["is_partition"]
    assert rep["n_offending"] > 100
    assert rep["n_uncovered"] == 2          # both endpoints
