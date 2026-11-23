#!/usr/bin/env python3
"""Verify the asymmetry refactor does not change the published validation.

The refactor retargets the asymmetry rules from the severity output to a
referral flag. The published validation runs a single-ear protocol with
asymmetry pinned to zero, so the invariant that makes that validation
metrics-neutral is structural: no rule reaching the severity consequent may
have an asymmetry antecedent, and the severity score must not depend on the
second ear at all.

This replaces the previous version of the script, which compared the test-set
FAI against ``archive/predictions_PRE_asymmetry_refactor.pkl`` by MD5. That
baseline was never committed (``archive/`` contains only MANUSCRIPT_OUTLINE.md)
and the split it rebuilt used a positional permutation of participants,
whereas the pipeline assigns test participants by a SEQN hash. It could not
have produced the committed vector even if the file had been present, so the
check was un-runnable rather than merely failing. The property tested here
needs no historical snapshot.
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fuzzy_audiogram import core  # noqa: E402

TOL = 1e-9


def _terms(node):
    """Flatten a scikit-fuzzy Term or nested TermAggregate into Terms."""
    if hasattr(node, 'parent'):
        yield node
        return
    for attr in ('term1', 'term2'):
        if hasattr(node, attr):
            yield from _terms(getattr(node, attr))


def _targets(rule, consequent_label):
    return any(w.term.parent.label == consequent_label
               for w in rule.consequent)


def check_no_asymmetry_path_to_severity():
    """No severity rule may be conditioned on asymmetry, in either mode."""
    checked = 0
    for single_ear in (True, False):
        system, *_ = core.build_audiogram_fis(single_ear=single_ear)
        rules = list(system.rules)
        severity_rules = [r for r in rules if _targets(r, 'severity')]
        offenders = [
            r for r in severity_rules
            if any(t.parent.label == 'asymmetry' for t in _terms(r.antecedent))
        ]
        checked += len(severity_rules)
        mode = 'single-ear' if single_ear else 'bilateral'
        print(f"  {mode:10} rule base {len(rules):2d} rules, "
              f"{len(severity_rules)} target severity, "
              f"{len(offenders)} take an asymmetry input")
        if offenders:
            for rule in offenders:
                print(f"    OFFENDER: {rule}")
            raise AssertionError(
                f"{len(offenders)} asymmetry rule(s) still reach severity in "
                f"{mode} mode")
    print(f"  no asymmetry antecedent reaches severity across {checked} rules")


def check_severity_ignores_the_second_ear():
    """Bilateral severity must equal the tested ear's single-ear severity."""
    cases = [
        ("symmetric normal",   [15] * 8, [15] * 8),
        ("borderline 26 dB",   [26] * 8, [36] * 8),
        ("mild asymmetry",     [30] * 8, [20] * 8),
        ("moderate asymmetry", [45] * 8, [25] * 8),
        ("severe asymmetry",   [65] * 8, [20] * 8),
        ("reviewer case D",    [55] * 8, [28] * 8),
        ("presbycusis",        [15, 20, 25, 35, 45, 55, 65, 70], [15] * 8),
    ]
    for name, left, right in cases:
        single = core.classify_audiogram(left)
        bilateral = core.classify_audiogram(left, right)
        delta = abs(float(single['fai_score']) - float(bilateral['fai_score']))
        print(f"    {name:20} FAI {single['fai_score']:6.2f} vs "
              f"{bilateral['fai_score']:6.2f}  {bilateral['fai_label']}")
        assert delta <= TOL, f"{name}: severity moved by {delta} with the second ear"
        assert single['fai_label'] == bilateral['fai_label'], name


def check_referral_responds_to_asymmetry():
    """Asymmetry must still drive referral urgency, monotonically."""
    levels = [0, 20, 35, 50]
    values = []
    for gap in levels:
        right = [30] * 8
        left = [30 + gap] * 8
        out = core.classify_audiogram(left, right)
        referral = out['outputs']['referral']
        assert referral['status'] == core.OUTPUT_DEFUZZIFIED, (gap, referral)
        values.append(referral['value'])
        print(f"    asymmetry {gap:2d} dB -> referral {referral['value']:6.2f}")
    assert all(b > a for a, b in zip(values, values[1:])), values


def main():
    print("Asymmetry refactor: metrics-neutrality checks")
    check_no_asymmetry_path_to_severity()
    print("\n  severity reflects the tested ear alone:")
    check_severity_ignores_the_second_ear()
    print("\n  referral still tracks inter-aural asymmetry:")
    check_referral_responds_to_asymmetry()
    print("\n  PASS asymmetry refactor is metrics-neutral")


if __name__ == '__main__':
    main()
