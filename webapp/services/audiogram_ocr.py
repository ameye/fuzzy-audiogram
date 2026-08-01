"""
audiogram_ocr.py — OpenCV-based OCR for clinical audiogram images.

Extracts raw threshold values (dB per frequency, per ear) from a
standard clinical audiogram image WITHOUT external OCR engines.

Pipeline:
  1. Grid calibration — detect the plot panel, horizontal dB gridlines,
     vertical frequency gridlines, and the dB-origin (via axis-label count).
  2. Symbol detection — HSV colour segmentation (red = right, blue = left),
     then connected-component analysis with shape classification
     (circle O / X / triangle Δ / square □).
  3. Coordinate mapping — symbol centroid (px) -> (frequency Hz, dB HL)
     via the calibrated axes.

Returns a structured result with per-ear threshold lists, plus confidence
flags so the caller can warn the user when something looks off.

Limitations (v1):
  - Assumes standard clinical layout: log-frequency x-axis, linear dB
    y-axis with 5/10 dB grid, red/blue symbol colours.
  - Single panel. Compound figures (multi-panel) should be cropped first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# Standard audiometric frequencies the framework understands
FRAMEWORK_FREQUENCIES = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]

SYMBOL_NAMES = {
    "circle": "O",
    "x": "X",
    "triangle": "T",
    "square": "S",
}

DEFAULT_DB_STEP = 5  # light gridline every 5 dB
DEFAULT_FREQ_LABELS = [125, 250, 500, 1000, 2000, 4000, 8000]


@dataclass
class OCRResult:
    thresholds_left: dict[int, float] = field(default_factory=dict)   # freq -> dB
    thresholds_right: dict[int, float] = field(default_factory=dict)
    masked_left: dict[int, float] = field(default_factory=dict)
    masked_right: dict[int, float] = field(default_factory=dict)
    symbols: list[dict] = field(default_factory=list)                 # raw detections
    calibration: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.thresholds_left or self.thresholds_right
                    or self.masked_left or self.masked_right)

    def as_dict(self) -> dict:
        return {
            "thresholds_left": self.thresholds_left,
            "thresholds_right": self.thresholds_right,
            "masked_left": self.masked_left,
            "masked_right": self.masked_right,
            "symbols": self.symbols,
            "calibration": self.calibration,
            "warnings": self.warnings,
            "success": self.success,
        }


# ---------------------------------------------------------------------------
# Grid calibration
# ---------------------------------------------------------------------------

def _detect_horizontal_lines(img_gray: np.ndarray, min_len_frac: float = 0.5) -> list[int]:
    """Return y-coordinates of horizontal grid lines (long dark rows)."""
    h, w = img_gray.shape
    _, bw = cv2.threshold(img_gray, 180, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * 0.4), 1))
    opened = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel)
    row_sums = opened.sum(axis=1)
    min_len = w * min_len_frac * 255
    return [y for y in range(h) if row_sums[y] > min_len]


def _detect_vertical_lines(img_gray: np.ndarray, min_len_frac: float = 0.4) -> list[int]:
    """Return x-coordinates of vertical grid lines (long dark columns)."""
    h, w = img_gray.shape
    _, bw = cv2.threshold(img_gray, 180, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h * 0.4)))
    opened = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel)
    col_sums = opened.sum(axis=0)
    min_len = h * min_len_frac * 255
    return [x for x in range(w) if col_sums[x] > min_len]


def _cluster(lines: list[int], tol: int = 6) -> list[int]:
    """Cluster nearby coordinates and return cluster centres."""
    if not lines:
        return []
    lines = sorted(lines)
    clusters = [[lines[0]]]
    for v in lines[1:]:
        if v - clusters[-1][-1] <= tol:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [int(np.mean(c)) for c in clusters]


def _count_axis_labels(img_gray: np.ndarray, panel_left: int, panel_top: int,
                       panel_bottom: int, left_strip_w: int = 40) -> int:
    """
    Count y-axis label rows in the strip left of the panel.

    This disambiguates the dB origin: 14 labels => -10..120 (top=-10),
    13 labels => 0..120 (top=0).
    """
    if panel_left < left_strip_w + 4:
        return 0
    # Extend upward past panel_top so the topmost label row isn't clipped
    strip_top = max(0, panel_top - 25)
    strip = img_gray[strip_top:panel_bottom, max(4, panel_left - left_strip_w):panel_left - 2]
    if strip.size == 0:
        return 0
    _, bw = cv2.threshold(strip, 170, 255, cv2.THRESH_BINARY_INV)
    row_sums = bw.sum(axis=1)
    # Find bands where dark pixels exist (label rows)
    bands = []
    in_band = False
    for y, s in enumerate(row_sums):
        if s > 10 and not in_band:
            in_band = True
            start = y
        elif s <= 10 and in_band:
            in_band = False
            bands.append((start, y))
    if in_band:
        bands.append((bands[-1][1] if bands else 0, len(row_sums)))
    # Filter tiny bands (noise)
    bands = [b for b in bands if b[1] - b[0] >= 4]
    return len(bands)


class AudiogramOCR:
    def __init__(
        self,
        frequencies: Optional[list[int]] = None,
        db_min: int = -10,
        db_max: int = 120,
        db_step: int = DEFAULT_DB_STEP,
        auto_db_origin: bool = True,
    ):
        self.frequencies = frequencies or DEFAULT_FREQ_LABELS
        self.db_min = db_min
        self.db_max = db_max
        self.db_step = db_step
        self.auto_db_origin = auto_db_origin

    # ------------------------------------------------------------------
    def extract(self, image_path: str | Path | np.ndarray) -> OCRResult:
        img = self._load(image_path)
        result = OCRResult()

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Upscale small images for better grid detection
        if gray.shape[0] < 500:
            scale = 700 / gray.shape[0]
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        h_lines = _cluster(_detect_horizontal_lines(gray))
        v_lines = _cluster(_detect_vertical_lines(gray))

        if len(h_lines) < 3 or len(v_lines) < 2:
            result.warnings.append(
                f"Grid detection weak: {len(h_lines)} h-lines, {len(v_lines)} v-lines. "
                "Is this a standard audiogram layout?"
            )
            return result

        # Panel = bounding box of interior gridlines
        panel_top = min(h_lines)
        panel_bottom = max(h_lines)
        panel_left = min(v_lines)
        panel_right = max(v_lines)

        # ---- dB calibration ----
        # Uniform gridline spacing => pixels per dB
        spacings = np.diff(h_lines)
        spacings = spacings[(spacings > 3) & (spacings < spacings.max() * 1.5)]
        px_per_step = float(np.median(spacings)) if len(spacings) else 0.0

        # dB origin: derive from grid line count when possible (27 lines = -10..120
        # at 5 dB step, 25 = 0..120, 23 = 10..120). Fall back to label counting.
        top_db = self.db_min
        if self.auto_db_origin:
            n_lines = len(h_lines)
            n_labels = _count_axis_labels(gray, panel_left, panel_top, panel_bottom)
            # Grid-line count is the most reliable signal
            if n_lines in (27, 25, 23):
                top_db = -10 + (27 - n_lines) * 10
            elif n_labels >= 11:
                top_db = -10 + (14 - n_labels) * 10
            result.calibration["label_count"] = n_labels
            result.calibration["h_line_count"] = n_lines

        px_per_db = px_per_step / self.db_step if px_per_step else 0.0

        # ---- Frequency calibration ----
        # Vertical gridlines at each frequency tick. Count tells us which set.
        v_spacings = np.diff(v_lines)
        v_spacings = v_spacings[v_spacings > 3]
        n_freq_ticks = len(v_lines)

        # Standard frequency sets by tick count
        freq_sets = {
            7: [125, 250, 500, 1000, 2000, 4000, 8000],
            6: [250, 500, 1000, 2000, 4000, 8000],
            8: [250, 500, 1000, 2000, 3000, 4000, 6000, 8000],
            5: [250, 500, 1000, 2000, 4000],
        }
        freqs = freq_sets.get(n_freq_ticks, self.frequencies)
        if len(freqs) != len(v_lines):
            freqs = self.frequencies[:len(v_lines)]

        result.calibration.update({
            "panel": [int(panel_left), int(panel_top), int(panel_right), int(panel_bottom)],
            "px_per_db": round(px_per_db, 3),
            "top_db": int(top_db),
            "h_lines": len(h_lines),
            "v_lines": len(v_lines),
            "frequencies": freqs,
        })

        if px_per_db <= 0:
            result.warnings.append("Could not determine pixels-per-dB; grid spacing unclear.")
            return result

        def y_to_db(y: int) -> float:
            # Clinical: lower on the plot (larger y) = higher dB
            return top_db + (y - panel_top) / px_per_db

        def x_to_freq(x: int) -> float:
            # log interpolation between the two nearest detected tick x's
            xs = np.array(v_lines, dtype=float)
            fs = np.array(freqs, dtype=float)
            if x <= xs[0]:
                return float(fs[0])
            if x >= xs[-1]:
                return float(fs[-1])
            logfs = np.log10(fs)
            # find bracketing interval
            i = int(np.searchsorted(xs, x)) - 1
            i = max(0, min(i, len(xs) - 2))
            x0, x1 = xs[i], xs[i + 1]
            f0, f1 = logfs[i], logfs[i + 1]
            frac = (x - x0) / (x1 - x0)
            return float(10 ** (f0 + frac * (f1 - f0)))

        # ---- Symbol detection ----
        symbols = self._detect_symbols(img, panel_left, panel_top, panel_right, panel_bottom)

        for s in symbols:
            freq = x_to_freq(s["x"])
            db = y_to_db(s["y"])
            s["frequency_hz"] = round(freq)
            s["db_hl"] = round(db, 1)
            result.symbols.append(s)

            target = None
            if s["kind"] == SYMBOL_NAMES["circle"]:
                target = result.thresholds_right
            elif s["kind"] == SYMBOL_NAMES["x"]:
                target = result.thresholds_left
            elif s["kind"] == SYMBOL_NAMES["triangle"]:
                target = result.masked_right
            elif s["kind"] == SYMBOL_NAMES["square"]:
                target = result.masked_left
            if target is not None:
                # Nearest clinical frequency label (keeps 125 Hz, 3k, 6k etc.)
                nf = min(self.frequencies, key=lambda f: abs(f - freq))
                if nf not in target or True:  # last symbol wins for overlapping
                    target[nf] = round(db, 1)

        if not result.success:
            result.warnings.append("No symbols detected. Check colours (red=right, blue=left) "
                                   "or try a cleaner image.")

        return result

    # ------------------------------------------------------------------
    def _load(self, image_path: str | Path | np.ndarray) -> np.ndarray:
        if isinstance(image_path, (str, Path)):
            img = cv2.imread(str(image_path))
            if img is None:
                raise ValueError(f"Cannot read image: {image_path}")
            return img
        return np.asarray(image_path)

    # ------------------------------------------------------------------
    def _detect_symbols(self, img, left, top, right, bottom):
        """Detect red/blue symbols inside the panel and classify shapes."""
        roi = img[top:bottom, left:right]
        symbols = []

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Red: two hue ranges (near 0 and near 180)
        red_mask = cv2.inRange(hsv, (0, 60, 60), (10, 255, 255)) | \
                   cv2.inRange(hsv, (170, 60, 60), (180, 255, 255))
        # Blue
        blue_mask = cv2.inRange(hsv, (95, 60, 60), (135, 255, 255))

        for color, mask in (("right", red_mask), ("left", blue_mask)):
            # Light close to merge strokes; skip aggressive open (would eat thin rings)
            cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            contours, hierarchy = cv2.findContours(cleaned, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

            for idx, cnt in enumerate(contours):
                area = cv2.contourArea(cnt)
                if area < 12:  # noise
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                # symbol size sanity vs panel
                if w > (right - left) * 0.08 or h > (bottom - top) * 0.15:
                    continue

                # child contour -> has a hole -> circle (O)
                has_child = hierarchy is not None and hierarchy[0][idx][2] != -1

                kind = self._classify_shape(cnt, has_child)
                cx = left + x + w / 2
                cy = top + y + h / 2

                symbols.append({
                    "kind": kind,
                    "x": float(cx),
                    "y": float(cy),
                    "area": int(area),
                    "w": int(w),
                    "h": int(h),
                    "ear": color,
                })

        return symbols

    # ------------------------------------------------------------------
    @staticmethod
    def _classify_shape(contour, has_child: bool) -> str:
        """Classify a symbol contour as circle / x / triangle / square.

        Returns the clinical letter code: 'O', 'X', 'T' (triangle) or 'S' (square).
        """
        # Perimeter / area ratio (isoperimetric quotient) — high for circles
        perimeter = cv2.arcLength(contour, True)
        area = cv2.contourArea(contour)
        if area <= 0 or perimeter <= 0:
            return "X"
        circularity = 4 * np.pi * area / (perimeter ** 2)

        # Approximate polygon
        approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)
        n_corners = len(approx)

        # Shape by corners FIRST — a triangle/square outline also has a hole,
        # so 'has_child' alone can't decide circle vs triangle.
        if n_corners <= 3:
            # triangle (Δ) — but a noisy circle could approximate to <4 corners;
            # high circularity disambiguates
            if circularity > 0.75:
                return "O"
            return "T"
        if n_corners == 4:
            if cv2.isContourConvex(approx):
                # square vs circle-ish blob: circularity disambiguates
                return "S" if circularity < 0.75 else "O"
            return "X"

        # Circle: ring (has child) or very round blob
        if has_child or circularity > 0.8:
            return "O"
        return "X"
