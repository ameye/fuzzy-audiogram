"""Regression tests for consequents that no rule supports.

The frozen FAI raised ``KeyError`` on 20 of 410 OAUTHC ears because
scikit-fuzzy omits a consequent from ``sim.output`` when it has nothing to
defuzzify. These tests pin the three-way status (defuzzified / unfired /
empty membership), the documented fallback policy, and the absence of
state leakage when a simulation object is reused.

Run with ``python -m pytest tests/test_unfired_consequents.py -q``.
"""

import copy
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fuzzy_audiogram import core  # noqa: E402
from fuzzy_audiogram.core import (  # noqa: E402
    OUTPUT_DEFUZZIFIED,
    OUTPUT_EMPTY,
    OUTPUT_UNFIRED,
    classify_audiogram,
)

# Thresholds in [250, 500, 1k, 2k, 3k, 4k, 6k, 8k] order.
NORMAL_EAR = [10, 10, 10, 10, 10, 10, 10, 10]
CEILING_EAR = [120, 120, 120, 120, 120, 120, 120, 120]
# study 13 of the OAUTHC export: severity resolves, configuration does not.
PARTIAL_EAR = [45, 50, 40, 50, 75, 85, 110, 100]


def test_all_consequents_fire():
    """A well-covered ear defuzzifies every consequent and gets no fallback."""
    result = classify_audiogram(NORMAL_EAR)

    assert result['unfired_consequents'] == []
    assert result['n_unfired_consequents'] == 0
    assert result['fai_label_source'] == 'fuzzy'
    assert result['configuration_source'] == 'fuzzy'
    assert result['fai_label'] == 'Normal'
    # The published index returns 'Flat' rather than 'Normal' for a flat,
    # entirely normal contour (the normal-shape rule competes with the flat
    # rule). That is pre-existing behaviour and is not changed here; what
    # matters is that no consequent went unfired.
    assert result['configuration_label'] != core.UNDETERMINED_SHAPE_LABEL
    assert result['fai_score'] is not None
    assert result['configuration_score'] is not None
    for status in result['outputs'].values():
        assert status['status'] == OUTPUT_DEFUZZIFIED


def test_ceiling_ear_is_covered_by_the_partition():
    """PTA 120 used to sit past the support of every severity function.

    Under the independently fitted feet the profound trapezoid closed at
    120 dB, so all six memberships were zero there and the severity consequent
    went unfired, falling back to the crisp grade. The Ruspini partition pads
    the outer feet 0.5 dB beyond the universe, so the ceiling is covered and
    the fallback is no longer reachable on that path.

    The fallback machinery is still exercised by
    ``test_status_separates_unfired_from_empty_membership`` and by the shape
    consequent; this test pins the coverage gain rather than the old gap.
    """
    result = classify_audiogram(CEILING_EAR)

    assert result['unfired_consequents'] == []
    assert result['outputs']['severity']['status'] == OUTPUT_DEFUZZIFIED
    assert result['outputs']['severity']['rule_support'] == pytest.approx(1.0)

    # A real fuzzy score, not a fallback.
    assert result['fai_score'] == pytest.approx(95.51, abs=0.01)
    assert result['fai_label'] == 'Profound'
    assert result['fai_label_source'] == 'fuzzy'

    # And the memberships still sum to one at that threshold.
    memberships = result['threshold_memberships']
    assert sum(memberships.values()) == pytest.approx(1.0, abs=1e-9)
    assert memberships['profound'] == pytest.approx(1.0, abs=1e-9)


def test_some_consequents_unfired():
    """Severity resolves while configuration does not: the study 13 pattern."""
    result = classify_audiogram(PARTIAL_EAR)

    assert result['unfired_consequents'] == ['audiogram_shape']
    assert result['n_unfired_consequents'] == 1
    assert result['outputs']['audiogram_shape']['status'] == OUTPUT_UNFIRED
    assert result['outputs']['audiogram_shape']['rule_support'] == 0.0

    assert result['fai_label_source'] == 'fuzzy'
    # 55.55 is what the Ruspini configuration produces for this contour. The
    # label is Moderate because the calibrated cut point for moderately severe
    # sits at 57.3, above this score.
    assert result['fai_score'] == pytest.approx(55.55, abs=0.01)
    assert result['fai_label'] == 'Moderate'

    assert result['configuration_label'] == core.UNDETERMINED_SHAPE_LABEL
    assert result['configuration_score'] is None
    assert result['configuration_source'] == 'undetermined'


def test_status_separates_unfired_from_empty_membership():
    """A rule that fires at zero support is not the same as one that fires.

    ``unfired`` means no rule had any antecedent truth. ``empty_membership``
    means a rule fired but the aggregated consequent function had no area, so
    the defuzzifier still produced nothing. scikit-fuzzy drops the key in both
    cases; the status must not.
    """
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl

    antecedent = ctrl.Antecedent(np.arange(0, 11, 1), 'x')
    antecedent['high'] = fuzz.trimf(antecedent.universe, [8, 10, 10])

    dead = ctrl.Consequent(np.arange(0, 11, 1), 'dead')
    dead['void'] = np.zeros(11)          # membership function with zero area
    untouched = ctrl.Consequent(np.arange(0, 11, 1), 'untouched')
    untouched['term'] = fuzz.trimf(untouched.universe, [0, 5, 10])

    rules = [ctrl.Rule(antecedent['high'], dead['void'])]
    sim = ctrl.ControlSystemSimulation(ctrl.ControlSystem(rules))
    sim.input['x'] = 10
    sim.compute()

    status, value, support = core._consequent_status(sim, dead)
    assert status == OUTPUT_EMPTY
    assert value is None
    assert support == pytest.approx(1.0)

    status, value, support = core._consequent_status(sim, untouched)
    assert status == OUTPUT_UNFIRED
    assert value is None
    assert support == 0.0


def test_reused_simulation_does_not_leak_between_ears():
    """One shared simulation object must not carry a previous ear's values.

    scikit-fuzzy only clears the consequent terms of the first rule it
    evaluates, so a reused ``ControlSystemSimulation`` can hand back the
    previous ear's score. This reproduces a real false result (a PTA of 120
    graded normal) and asserts that the per-call reset removes it.
    """
    original = core.build_audiogram_fis
    built = original(single_ear=True)

    def shared_build(single_ear=False):
        return built                      # same object every call, deliberately

    core.build_audiogram_fis = shared_build
    try:
        first = classify_audiogram(NORMAL_EAR)
        second = classify_audiogram(CEILING_EAR)
    finally:
        core.build_audiogram_fis = original

    assert first['fai_label'] == 'Normal'
    # The ceiling ear is covered by the partition, so it now defuzzifies. The
    # point of the test is that it returns its own score, not the normal ear's.
    assert second['outputs']['severity']['status'] == OUTPUT_DEFUZZIFIED
    assert second['fai_score'] == pytest.approx(95.51, abs=0.01)
    assert second['fai_score'] != first['fai_score']
    assert second['fai_label'] == 'Profound'
    assert second['unfired_consequents'] == []


SYNTHETIC_CASES = [
    [120] * 8,
    [0] * 8,
    [-5] * 8,
    [0, 120, 0, 120, 0, 120, 0, 120],
    [120, 0, 120, 0, 120, 0, 120, 0],
    [50, 45, 60, 120, 120, 120, 120, 95],
    [0, 0, 5, 120, 0, 120, 0, 120],
    [95, 95, 95, 95, 95, 95, 95, 95],
    [26, 30, 39, 44, 45, 55, 65, 75],
]


@pytest.mark.parametrize('thresholds', SYNTHETIC_CASES)
def test_extreme_inputs_do_not_raise(thresholds):
    """Edge and discontinuous contours return a classified ear, never an error."""
    result = classify_audiogram(thresholds)

    assert isinstance(result['n_unfired_consequents'], int)
    assert result['fai_label']
    assert result['configuration_label']
    if result['fai_score'] is None:
        assert result['fai_label_source'] == 'crisp_who_fallback'
    else:
        assert result['fai_label_source'] == 'fuzzy'


RAW = ROOT / 'oatuhc_eda' / 'raw_export.csv'


@pytest.mark.skipif(not RAW.exists(),
                    reason='OAUTHC export is patient-level and git-ignored')
def test_validation_set_never_raises():
    """Every ear of the OAUTHC validation export classifies without an error.

    The export is not vendored, so this runs only where the file is present.
    It goes through the service layer, which is the path the validation
    analysis actually uses (sparse-frequency interpolation included).
    """
    pd = pytest.importorskip('pandas')

    sys.path.insert(0, str(ROOT / 'webapp'))
    from services import fai_service

    columns = ['th_250', 'th_500', 'th_1k', 'th_2k', 'th_3k', 'th_4k',
               'th_6k', 'th_8k']
    frequencies = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
    frame = pd.read_csv(RAW)

    built = core.build_audiogram_fis(single_ear=True)
    original = core.build_audiogram_fis
    core.build_audiogram_fis = lambda single_ear=False: copy.deepcopy(built)
    results = []
    try:
        for _, row in frame.iterrows():
            values = {f: float(row[c]) for c, f in zip(columns, frequencies)
                      if pd.notna(row[c])}
            results.append(fai_service.classify_values(thresholds_left=values))
    finally:
        core.build_audiogram_fis = original

    assert len(results) == len(frame)
    assert not [r for r in results if 'error' in r]

    fallbacks = [r for r in results if r['fai_label_source'] != 'fuzzy']
    undetermined = [r for r in results
                    if r['configuration_source'] == 'undetermined']

    # The fix is only sound if the fallback stays rare; a large share would
    # mean the rule base, not the code, is the problem.
    assert len(fallbacks) <= 0.05 * len(frame)
    assert len(undetermined) <= 0.05 * len(frame)
    for result in results:
        assert result['n_unfired_consequents'] in (0, 1, 2)
