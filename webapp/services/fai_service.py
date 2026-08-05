"""
fai_service.py — Bridge between raw threshold values / OCR output and the
fuzzy_audiogram FIS classification.

Handles:
  - Mapping sparse frequency->dB dicts (from OCR or manual entry) onto the
    framework's canonical 8-frequency array [250, 500, 1000, 2000, 3000,
    4000, 6000, 8000], with linear-in-log-frequency interpolation.
  - Running classify_audiogram() and shaping the result into a clean
    API-friendly response.
  - Rendering a PNG audiogram of the values (for UI previews).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

# Canonical frequencies used by the fuzzy framework
CANONICAL_FREQS = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]

log = logging.getLogger(__name__)

# Import the fuzzy package lazily so the web app can start even if the
# scientific stack is not yet installed.
_fuzzy = None


def _get_fuzzy():
    global _fuzzy
    if _fuzzy is None:
        import sys
        from pathlib import Path as P

        # Package lives at <repo>/fuzzy_audiogram — add to path if needed
        repo = P(__file__).resolve().parent.parent.parent
        pkg_dir = repo / "fuzzy_audiogram"
        if pkg_dir.exists() and str(pkg_dir) not in sys.path:
            sys.path.insert(0, str(repo))
        from fuzzy_audiogram import (
            classify_audiogram,
            compute_audiogram_features,
            crisp_classify,
        )
        _fuzzy = {"classify": classify_audiogram,
                  "features": compute_audiogram_features,
                  "crisp": crisp_classify}
    return _fuzzy


def interpolate_to_canonical(values: dict[int, float],
                             target_freqs: Optional[list[int]] = None) -> list[Optional[float]]:
    """
    Map a sparse {frequency_hz: db} dict onto the canonical frequency array.

    Uses nearest-neighbour for exact matches and linear interpolation in
    log-frequency space for gaps. Returns a list aligned to target_freqs
    (None where no data and no interpolation possible).
    """
    target_freqs = target_freqs or CANONICAL_FREQS
    if not values:
        return [None] * len(target_freqs)

    freqs = sorted(values.keys())
    dbs = [values[f] for f in freqs]

    out = []
    for tf in target_freqs:
        if tf in values:
            out.append(values[tf])
            continue
        # interpolate in log space
        if tf < freqs[0]:
            out.append(dbs[0] if len(freqs) >= 1 else None)
            continue
        if tf > freqs[-1]:
            out.append(dbs[-1] if len(freqs) >= 1 else None)
            continue
        # find bracketing pair
        for i in range(len(freqs) - 1):
            if freqs[i] <= tf <= freqs[i + 1]:
                f0, f1 = freqs[i], freqs[i + 1]
                d0, d1 = dbs[i], dbs[i + 1]
                if f1 == f0:
                    out.append(d0)
                    break
                t = (np.log10(tf) - np.log10(f0)) / (np.log10(f1) - np.log10(f0))
                out.append(round(d0 + t * (d1 - d0), 1))
                break
        else:
            out.append(None)
    return out


def classify_values(thresholds_left: Optional[dict[int, float]] = None,
                    thresholds_right: Optional[dict[int, float]] = None,
                    masked_left: Optional[dict[int, float]] = None,
                    masked_right: Optional[dict[int, float]] = None,
                    ear: str = "both") -> dict:
    """
    Classify an audiogram from sparse frequency->dB dicts.

    If thresholds_left is None but right is provided, uses right for
    classification (and vice versa). 'ear' chooses which side drives the
    primary FAI: 'left', 'right', or 'better' (the side with the lower PTA).

    Returns a dict with FAI, labels, features, crisp reference, and the
    interpolated arrays.
    """
    fuzzy = _get_fuzzy()

    # Choose the driving ear
    left = thresholds_left or {}
    right = thresholds_right or {}

    if ear == "better":
        pta_l = _approx_pta(left)
        pta_r = _approx_pta(right)
        if pta_r is not None and (pta_l is None or pta_r < pta_l):
            primary = right
        else:
            primary = left
    elif ear == "right":
        primary = right
    else:  # 'left' or 'both' (both defaults to left-primary)
        primary = left

    # Interpolate to canonical array
    left_arr = interpolate_to_canonical(left)
    right_arr = interpolate_to_canonical(right)
    primary_arr = interpolate_to_canonical(primary)

    if not any(v is not None for v in primary_arr):
        return {"error": "No threshold data to classify."}

    # Fill None with nearest available for the FIS (FIS expects full arrays)
    def fill(arr):
        arr = list(arr)
        # forward fill
        last = None
        for i, v in enumerate(arr):
            if v is None:
                arr[i] = last
            else:
                last = v
        # backward fill
        last = None
        for i in range(len(arr) - 1, -1, -1):
            if arr[i] is None:
                arr[i] = last
            else:
                last = arr[i]
        return arr

    primary_filled = fill(primary_arr)
    left_filled = fill(left_arr)
    right_filled = fill(right_arr)

    # Add left-ear (or right-ear) as the 'other' ear for asymmetry
    # Only pass it when we actually have data (all-None confuses the FIS)
    other = None
    if primary is left and any(v is not None for v in right_filled):
        other = right_filled
    elif primary is right and any(v is not None for v in left_filled):
        other = left_filled

    try:
        result = fuzzy["classify"](primary_filled, other)
    except Exception as e:
        log.warning("FIS classification failed: %s", e)
        return {"error": f"Classification failed: {e}"}

    # Clean up the result into API shape
    feats = result.get("features", {})
    pta = result.get("pt4a") or feats.get("pta")

    # Data-quality transparency: which canonical frequencies were measured
    # directly vs inferred (interpolated / edge-held / filled) by the FIS.
    def quality(measured: dict) -> dict:
        measured_freqs = [f for f in CANONICAL_FREQS if f in measured]
        inferred = [f for f in CANONICAL_FREQS if f not in measured_freqs]
        return {
            "measured": measured_freqs,
            "inferred": inferred,
            "coverage": round(len(measured_freqs) / len(CANONICAL_FREQS), 2),
        }

    dq_left = quality(left)
    dq_right = quality(right)
    dq_primary = quality(primary)

    warnings = []
    for side, dq in (("left", dq_left), ("right", dq_right)):
        if dq["coverage"] < 0.5:
            warnings.append(
                f"{side.capitalize()} ear: only {len(dq['measured'])}/8 frequencies "
                f"measured — {len(dq['inferred'])} values inferred by interpolation; "
                "interpret with caution."
            )

    return {
        "fai_score": round(result.get("fai_score", 0), 2),
        "fai_label": result.get("fai_label", "unknown"),
        "configuration_label": result.get("configuration_label", "unknown"),
        "configuration_score": round(result.get("configuration_score", 0), 2),
        "pta": round(pta, 1) if pta is not None else None,
        "crisp_label": fuzzy["crisp"](pta) if pta is not None else None,
        "ear_used": ear,
        "threshold_memberships": result.get("threshold_memberships", {}),
        "slope_memberships": result.get("slope_memberships", {}),
        "features": {
            "slope": round(feats.get("slope", 0), 2),
            "notch_depth": round(feats.get("notch_depth", 0), 2),
            "asymmetry": round(feats.get("asymmetry", 0), 2),
        },
        "arrays": {
            "frequencies": CANONICAL_FREQS,
            "left": left_filled,
            "right": right_filled,
            "primary": primary_filled,
        },
        "data_quality": {
            "left": dq_left,
            "right": dq_right,
            "primary": dq_primary,
        },
        "warnings": warnings,
    }


def classify_compare(thresholds_left: Optional[dict[int, float]] = None,
                     thresholds_right: Optional[dict[int, float]] = None,
                     masked_left: Optional[dict[int, float]] = None,
                     masked_right: Optional[dict[int, float]] = None) -> dict:
    """Classify BOTH ears independently and return a side-by-side comparison.

    Each ear runs the full FIS (the other ear is still passed for the
    asymmetry feature). 'better' is the ear with the lower PTA-4.
    """
    left_res = classify_values(thresholds_left, thresholds_right,
                               masked_left, masked_right, ear="left")
    right_res = classify_values(thresholds_left, thresholds_right,
                                masked_left, masked_right, ear="right")

    better = None
    delta = {}
    if "error" not in left_res and "error" not in right_res:
        l_pta = left_res.get("pta")
        r_pta = right_res.get("pta")
        if r_pta is not None and (l_pta is None or r_pta < l_pta):
            better = "right"
        elif l_pta is not None:
            better = "left"
        delta = {
            "fai_delta": round(left_res.get("fai_score", 0) - right_res.get("fai_score", 0), 2),
            "pta_delta": round((l_pta or 0) - (r_pta or 0), 1),
        }

    return {
        "mode": "compare",
        "left": left_res,
        "right": right_res,
        "better": better,
        "delta": delta,
    }


def _approx_pta(values: dict[int, float]) -> Optional[float]:
    """PTA-4 approximation from whatever frequencies are present."""
    if not values:
        return None
    pts = [values[f] for f in (500, 1000, 2000, 4000) if f in values]
    if not pts:
        pts = list(values.values())
    return float(np.mean(pts)) if pts else None


def render_audiogram_png(values_left: Optional[dict[int, float]] = None,
                         values_right: Optional[dict[int, float]] = None,
                         masked_left: Optional[dict[int, float]] = None,
                         masked_right: Optional[dict[int, float]] = None,
                         title: str = "Audiogram",
                         save_path: str | Path = "/tmp/audiogram_preview.png") -> str:
    """Render a preview PNG using the renderer (for UI display)."""
    from .audiogram_renderer import render_audiogram

    # Align sparse dicts onto renderer's frequency order
    renderer_freqs = [125, 250, 500, 1000, 2000, 4000, 8000]

    def to_list(vals):
        return [vals.get(f) if vals else None for f in renderer_freqs]

    path = render_audiogram(
        thresholds_left=to_list(values_left),
        thresholds_right=to_list(values_right),
        masked_left=to_list(masked_left),
        masked_right=to_list(masked_right),
        title=title,
        save_path=save_path,
    )
    return str(path)
