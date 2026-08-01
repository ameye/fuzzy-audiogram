# 🦻 FAI Calculator — Web App

A web-based **Fuzzy Audiometric Index (FAI) Calculator** with built-in
**audiogram OCR** — upload a photo/scan of a clinical audiogram and get
raw threshold values + fuzzy classification. Also exposes a REST API for
EHR integration.

Built on the [`fuzzy_audiogram`](../fuzzy_audiogram/) FIS package
(48-rule Mamdani inference, κ = 0.89 vs WHO PTA-4 reference).

## Features

| Feature | Endpoint | Description |
|---------|----------|-------------|
| Web UI | `GET /` | Manual entry + OCR upload, dark glass UI |
| Manual classify | `POST /api/classify` | JSON thresholds → FAI + config + memberships |
| Audiogram OCR | `POST /api/ocr` | Image → per-ear threshold dict (pure OpenCV, no tesseract) |
| OCR + classify | `POST /api/ocr-classify` | One-shot: image → thresholds → FAI |
| Sample image | `GET /api/sample?case=noise_notch` | Generate test audiogram PNG |
| FHIR stub | `GET /api/fhir/observation` | EHR integration contract |

## Quick Start

```bash
# From the repo root (so the fuzzy_audiogram package resolves)
pip install -e . && pip install -r webapp/requirements.txt
cd webapp
uvicorn main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

### Docker

```bash
cd webapp
docker compose up -d     # builds from repo root, runs on :8000
```

## OCR Capabilities

The OCR engine (`services/audiogram_ocr.py`) uses **pure OpenCV** — no
external OCR engines — so it runs anywhere:

1. **Grid calibration** — detects the plot panel, horizontal dB gridlines
   (5/10 dB), and vertical frequency gridlines. dB origin inferred from
   gridline count (27 lines = −10…120 dB).
2. **Symbol detection** — HSV colour segmentation (red = right ear,
   blue = left ear) + connected-component analysis.
3. **Shape classification** — circle `O` / cross `X` / triangle `Δ` /
   square `□` by corner count + circularity.
4. **Coordinate mapping** — symbol centroid → (frequency, dB) via the
   calibrated axes; log-interpolation for off-grid frequencies.

### Accuracy

Round-trip tests against synthetically rendered clinical audiograms:

| Case | Mean abs error |
|------|---------------|
| Normal | 0.3 dB |
| Noise notch | 0.5 dB |
| Presbycusis | 0.6 dB |
| Asymmetric | 0.6 dB |
| Masked (overlapping symbols) | 3.6 dB |

Run the tests:

```bash
cd webapp && python -m pytest tests/ -v
```

## API Examples

### Classify from JSON

```bash
curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"thresholds_left":{"250":20,"500":25,"1000":30,"2000":35,"4000":40,"8000":50},
       "thresholds_right":{"250":40,"500":45,"1000":50,"2000":55,"4000":60,"8000":70}}'
```

Returns FAI score, label, configuration, PTA-4, crisp reference, and
membership degrees.

### OCR an audiogram image

```bash
curl -F "file=@audiogram.png" http://localhost:8000/api/ocr
```

Returns:
```json
{
  "thresholds_left": {"250": 12, "500": 15, ...},
  "thresholds_right": {"250": 10, "500": 12, ...},
  "masked_left": {}, "masked_right": {},
  "calibration": {"px_per_db": 4.2, "top_db": -10, "frequencies": [...]},
  "warnings": []
}
```

## Known Limitations (v1)

- Assumes standard clinical layout: log-frequency x-axis, linear dB y-axis,
  red/blue symbol colours, 5/10 dB grid.
- Single-panel images — multi-panel figures should be cropped first.
- Masked (Δ/□) symbols can be confused with unmasked when overlapping.
- FHIR endpoint is a stub (contract only) — connect a real FHIR server
  for production EHR reads.
