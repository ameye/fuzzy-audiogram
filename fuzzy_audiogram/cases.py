"""The four clinical archetypes used in the manuscript and the deck.

These are synthetic illustrations, not records from the analysis cohort, and the
threshold arrays are stated explicitly so every reported FAI value can be
reproduced. They live in one place because the manuscript text, the case table,
Figure 4 and the conference deck must all describe the same audiograms; before
this module existed the figure used a different set of arrays from the table and
the two disagreed on every case.
"""

CASES = {
    # key: (display label, left thresholds, right thresholds or None)
    "A_BorderlineMild": ("A", [25, 25, 25, 30, 30, 30, 30, 30], None),
    "B_NoiseNotch": ("B", [15, 10, 10, 20, 15, 50, 50, 20], None),
    "C_Presbycusis": ("C", [20, 20, 25, 35, 45, 55, 60, 65], None),
    "D_Asymmetric": ("D", [50, 55, 55, 55, 55, 55, 55, 55],
                     [25, 25, 30, 30, 30, 30, 30, 30]),
}

# One-line clinical description, used by the figure panels.
TITLES = {
    "A_BorderlineMild": "Case A: Borderline mild",
    "B_NoiseNotch": "Case B: Noise notch",
    "C_Presbycusis": "Case C: Presbycusis",
    "D_Asymmetric": "Case D: Asymmetric loss",
}
