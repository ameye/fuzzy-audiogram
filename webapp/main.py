"""
FAI Calculator — FastAPI web app + REST API.

Endpoints:
  GET  /                  → web UI (static/index.html)
  POST /api/classify      → classify from JSON threshold values
  POST /api/ocr           → OCR an audiogram image → raw thresholds
  POST /api/ocr-classify  → OCR + classify in one step
  GET  /api/sample        → generate a sample audiogram image
  GET  /api/health        → health check
  GET  /api/fhir/observation → FHIR Observation stub (EHR integration)

Run:
  uvicorn main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from services import fai_service
from services.audiogram_ocr import AudiogramOCR

app = FastAPI(title="Fuzzy Audiogram FAI Calculator", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
OCR = AudiogramOCR()

# Mount static assets (CSS/JS/images) if the directory exists
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")


@app.get("/")
async def index():
    """Serve the web UI."""
    index_html = STATIC_DIR / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    return JSONResponse({"error": "UI not built"}, 500)


@app.get("/api/health")
async def health():
    try:
        fai_service._get_fuzzy()
        fuzzy_ok = True
    except Exception as e:
        fuzzy_ok = False
        err = str(e)
    return {
        "status": "ok",
        "fuzzy_backend": fuzzy_ok,
        "error": err if not fuzzy_ok else None,
    }


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _parse_threshold_dict(data: dict, key: str) -> dict[int, float]:
    """Convert {freq: db} (or {freq: {left/right}}) into int->float dict."""
    out = {}
    raw = data.get(key) or {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        try:
            out[int(float(k))] = float(v)
        except (TypeError, ValueError):
            continue
    return out


@app.post("/api/classify")
async def api_classify(payload: dict):
    """Classify an audiogram from JSON.

    Expects:
      {
        "thresholds_left":  {"250": 20, "500": 25, ...},   # optional
        "thresholds_right": {...},                           # optional
        "masked_left":      {...},                           # optional
        "masked_right":     {...},                           # optional
        "ear": "left" | "right" | "better"                   # optional, default both
      }
    """
    try:
        left = _parse_threshold_dict(payload, "thresholds_left")
        right = _parse_threshold_dict(payload, "thresholds_right")
        masked_left = _parse_threshold_dict(payload, "masked_left")
        masked_right = _parse_threshold_dict(payload, "masked_right")
        ear = payload.get("ear", "both")

        result = fai_service.classify_values(
            thresholds_left=left or None,
            thresholds_right=right or None,
            masked_left=masked_left or None,
            masked_right=masked_right or None,
            ear=ear,
        )
        if "error" in result:
            return JSONResponse({"error": result["error"]}, 400)
        return result
    except Exception as e:
        return JSONResponse({"error": f"Classification failed: {e}"}, 500)


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

@app.post("/api/ocr")
async def api_ocr(file: UploadFile = File(...)):
    """OCR an audiogram image → raw threshold values.

    Upload an image file; returns per-ear thresholds, masked values,
    calibration info and warnings.
    """
    try:
        data = await file.read()
        suffix = Path(file.filename or "upload.png").suffix or ".png"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            result = OCR.extract(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        return result.as_dict()
    except Exception as e:
        return JSONResponse({"error": f"OCR failed: {e}"}, 500)


@app.post("/api/ocr-classify")
async def api_ocr_classify(file: UploadFile = File(...)):
    """OCR an audiogram image AND classify it in one step."""
    try:
        data = await file.read()
        suffix = Path(file.filename or "upload.png").suffix or ".png"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            ocr_result = OCR.extract(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if not ocr_result.success:
            return JSONResponse({
                "error": "No audiogram symbols detected in the image.",
                "warnings": ocr_result.warnings,
            }, 422)

        classification = fai_service.classify_values(
            thresholds_left=ocr_result.thresholds_left or None,
            thresholds_right=ocr_result.thresholds_right or None,
            masked_left=ocr_result.masked_left or None,
            masked_right=ocr_result.masked_right or None,
            ear="better",
        )
        if "error" in classification:
            return JSONResponse({"error": classification["error"], "warnings": ocr_result.warnings}, 422)

        return {
            "ocr": ocr_result.as_dict(),
            "classification": classification,
        }
    except Exception as e:
        return JSONResponse({"error": f"OCR+classify failed: {e}"}, 500)


@app.get("/api/sample")
async def api_sample(case: str = Query("noise_notch")):
    """Generate a sample audiogram PNG for testing the OCR."""
    from services.audiogram_renderer import render_audiogram

    cases = {
        "normal": {"left": [10, 12, 15, 12, 14, 18, 20], "right": [8, 10, 12, 10, 12, 16, 18]},
        "noise_notch": {"left": [10, 12, 15, 35, 50, 55, 45], "right": [10, 12, 15, 40, 55, 60, 50]},
        "presbycusis": {"left": [15, 20, 30, 45, 60, 70, 75], "right": [15, 20, 30, 45, 60, 70, 75]},
        "asymmetric": {"left": [20, 25, 30, 35, 40, 45, 50], "right": [40, 45, 50, 55, 60, 65, 70]},
    }
    case_data = cases.get(case, cases["noise_notch"])
    path = render_audiogram(
        thresholds_left=case_data.get("left"),
        thresholds_right=case_data.get("right"),
        title=f"Sample: {case.replace('_', ' ').title()}",
        save_path=tempfile.mktemp(suffix=".png"),
    )
    return FileResponse(path, media_type="image/png")


# ---------------------------------------------------------------------------
# EHR / FHIR integration stub
# ---------------------------------------------------------------------------

@app.get("/api/fhir/observation")
async def fhir_observation(
    patient_id: str = Query("..."),
    category: str = Query("hearing"),
):
    """Return a minimal FHIR Observation bundle for hearing thresholds.

    This is a stub demonstrating the EHR integration contract. In production
    it would read from a FHIR server (e.g. HAPI) or an EHR API.
    """
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 0,
        "entry": [],
        "note": "FHIR integration stub — connect a real FHIR server (HAPI/Epic/Cerner) to serve Observation resources.",
        "query": {"patient_id": patient_id, "category": category},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
