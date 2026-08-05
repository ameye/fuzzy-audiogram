"""Tests for the FAI Calculator web app: renderer, OCR, and FAI service."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.audiogram_renderer import demo_cases, generate_demo_images, render_audiogram
from services.audiogram_ocr import AudiogramOCR
from services.fai_service import classify_values, interpolate_to_canonical

OCR = AudiogramOCR()


@pytest.fixture(scope="module")
def demo_images(tmp_path_factory):
    return generate_demo_images(str(tmp_path_factory.mktemp("audiograms")))


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def test_renderer_creates_image():
    p = render_audiogram(thresholds_left=[10, 20, 30, 40, 50, 60, 70],
                         save_path="/tmp/test_render.png")
    assert p.exists()
    assert p.stat().st_size > 1000


def test_renderer_demo_cases_have_expected_keys():
    for name, case in demo_cases().items():
        assert "left" in case
        assert "right" in case


# ---------------------------------------------------------------------------
# OCR accuracy (round-trip against known ground truth)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_name,tolerance", [
    ("normal", 2.0),
    ("noise_notch", 2.0),
    ("presbycusis", 2.0),
    ("asymmetric", 2.0),
    # masked case has overlapping symbols -> slightly looser
    ("masked", 5.0),
])
def test_ocr_roundtrip_accuracy(demo_images, case_name, tolerance):
    case = demo_cases()[case_name]
    path = demo_images[case_name]
    res = OCR.extract(path)

    assert res.success, f"{case_name}: no symbols detected — {res.warnings}"

    # Compare left + right thresholds where ground truth exists
    gt_left = dict(zip([125, 250, 500, 1000, 2000, 4000, 8000], case.get("left", [])))
    gt_right = dict(zip([125, 250, 500, 1000, 2000, 4000, 8000], case.get("right", [])))

    errors = []
    for freq, gt in gt_left.items():
        if freq in res.thresholds_left:
            errors.append(abs(res.thresholds_left[freq] - gt))
    for freq, gt in gt_right.items():
        if freq in res.thresholds_right:
            errors.append(abs(res.thresholds_right[freq] - gt))

    assert errors, f"{case_name}: no matching points to compare"
    mean_err = sum(errors) / len(errors)
    assert mean_err <= tolerance, (
        f"{case_name}: mean abs error {mean_err:.1f} dB exceeds {tolerance} dB "
        f"({len(errors)} points). Got left={res.thresholds_left}, right={res.thresholds_right}"
    )


def test_ocr_detects_masked_symbols(demo_images):
    res = OCR.extract(demo_images["masked"])
    assert res.masked_left or res.masked_right, "Masked symbols not detected"


def test_ocr_rejects_empty_image(tmp_path):
    from PIL import Image
    blank = tmp_path / "blank.png"
    Image.new("RGB", (400, 300), "white").save(blank)
    res = OCR.extract(str(blank))
    assert not res.success


# ---------------------------------------------------------------------------
# FAI service
# ---------------------------------------------------------------------------

def test_interpolate_to_canonical_handles_125hz():
    vals = {125: 10, 250: 12, 500: 15, 1000: 12, 2000: 14, 4000: 18, 8000: 20}
    out = interpolate_to_canonical(vals)
    assert len(out) == 8
    assert out[0] == 12       # 250 Hz
    assert out[2] == 12       # 1000 Hz
    assert out[4] is not None  # 3000 Hz interpolated
    assert out[6] is not None  # 6000 Hz interpolated


def test_classify_single_ear():
    res = classify_values(thresholds_left={250: 20, 500: 25, 1000: 30, 2000: 35, 4000: 40, 8000: 50})
    assert "error" not in res
    assert res["fai_label"] in {"Normal", "Mild", "Moderate", "Moderately Severe", "Severe", "Profound"}


def test_classify_both_ears_uses_asymmetry():
    # Left is the BETTER ear here (PTA ~32.5 vs right ~52.5) — the asymmetry
    # upgrade must NOT inflate the better ear's FAI, so its asymmetry feature
    # is 0. The worse ear carries the asymmetry signal.
    res_left = classify_values(
        thresholds_left={250: 20, 500: 25, 1000: 30, 2000: 35, 4000: 40, 8000: 50},
        thresholds_right={250: 40, 500: 45, 1000: 50, 2000: 55, 4000: 60, 8000: 70},
        ear="left",
    )
    assert res_left["features"]["asymmetry"] == 0, "better ear must not be asymmetry-upgraded"

    res_right = classify_values(
        thresholds_left={250: 20, 500: 25, 1000: 30, 2000: 35, 4000: 40, 8000: 50},
        thresholds_right={250: 40, 500: 45, 1000: 50, 2000: 55, 4000: 60, 8000: 70},
        ear="right",
    )
    assert res_right["features"]["asymmetry"] > 0, "worse ear should report the asymmetry signal"


def test_classify_flat_20db_not_inflated_by_worse_contralateral():
    # Regression: a normal ear (20 dB flat) next to a severely impaired
    # contralateral ear must stay Normal, not jump to Moderate (~48).
    twenties = {250: 20, 500: 20, 1000: 20, 2000: 20, 3000: 20, 4000: 20, 6000: 20, 8000: 20}
    sample_right = {250: 45, 500: 50, 1000: 55, 2000: 60, 3000: 65, 4000: 70, 6000: 75, 8000: 80}
    res = classify_values(thresholds_left=twenties, thresholds_right=sample_right, ear="left")
    assert res["pta"] == 20.0
    assert res["fai_score"] < 20, f"flat 20 dB ear inflated to FAI {res['fai_score']}"
    assert res["fai_label"] == "Normal"


def test_classify_empty_returns_error():
    res = classify_values(thresholds_left={})
    assert "error" in res
