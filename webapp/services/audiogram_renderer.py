"""
audiogram_renderer.py — Synthetic clinical audiogram generator.

Generates standard clinical-style audiogram images (grid + symbols) from
raw threshold values. Used to (a) test the OCR pipeline against known
ground truth, and (b) provide a "sample" endpoint in the web app.

Symbol conventions (standard clinical):
  O  — right ear, air conduction, unmasked   (red)
  X  — left ear,  air conduction, unmasked   (blue)
  Δ  — right ear, air conduction, masked     (red)
  □  — left ear,  air conduction, masked     (blue)

The renderer mimics common clinical audiogram paper:
  - X axis: 125, 250, 500, 1000, 2000, 4000, 8000 Hz (log-spaced)
  - Y axis: -10 to 120 dB HL, gridlines every 5 dB (light) / 10 dB (heavy)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Standard frequencies (log-spaced on the audiogram)
FREQUENCIES = [125, 250, 500, 1000, 2000, 4000, 8000]
DB_MIN = -10
DB_MAX = 120
DB_STEP = 5

# Color palette (RGB)
COLOR_RED = (220, 60, 60)
COLOR_BLUE = (40, 80, 220)
COLOR_GRID = (120, 120, 125)
COLOR_GRID_HEAVY = (70, 70, 75)
COLOR_AXIS = (30, 30, 35)
COLOR_BG = (250, 250, 252)

SYMBOL_O = "O"   # right unmasked
SYMBOL_X = "X"   # left unmasked
SYMBOL_TRI = "T"  # right masked (delta)
SYMBOL_SQ = "S"  # left masked (square)


def _try_font(sizes=(16, 14, 12)):
    """Return the best available TTF font, or None (PIL default)."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for size in sizes:
        for cand in candidates:
            p = Path(cand)
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    continue
    return None


def draw_symbol(draw: ImageDraw.ImageDraw, cx, cy, symbol, color, size=16):
    """Draw a clinical audiogram symbol centred at (cx, cy)."""
    r = size // 2
    if symbol == SYMBOL_O:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)
    elif symbol == SYMBOL_X:
        off = int(r * 0.7)
        draw.line([cx - off, cy - off, cx + off, cy + off], fill=color, width=3)
        draw.line([cx - off, cy + off, cx + off, cy - off], fill=color, width=3)
    elif symbol == SYMBOL_TRI:
        draw.polygon([(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)],
                     outline=color, width=3)
    elif symbol == SYMBOL_SQ:
        draw.rectangle([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)


def render_audiogram(
    thresholds_left: list[float] | None = None,
    thresholds_right: list[float] | None = None,
    masked_left: list[float] | None = None,
    masked_right: list[float] | None = None,
    frequencies: list[int] | None = None,
    width: int = 1000,
    height: int = 700,
    db_min: int = DB_MIN,
    db_max: int = DB_MAX,
    title: str = "",
    save_path: str | Path = "audiogram.png",
) -> Path:
    """
    Render a clinical audiogram image.

    thresholds_left/right: dB values, one per frequency (None = ear not tested).
    masked_left/right:     dB values plotted as masked symbols (Δ / □).
    """
    freqs = frequencies or FREQUENCIES
    n_freqs = len(freqs)

    # Layout geometry
    margin_l, margin_r = 90, 40
    margin_t, margin_b = 70, 90
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b

    db_range = db_max - db_min

    def freq_to_x(f):
        # log-spaced x within plot area
        log_min, log_max = np.log10(min(freqs)), np.log10(max(freqs))
        if log_max == log_min:
            return margin_l + plot_w / 2
        t = (np.log10(f) - log_min) / (log_max - log_min)
        return margin_l + t * plot_w

    def db_to_y(db):
        # Clinical convention: LOW dB (e.g. -10) at TOP, HIGH dB (e.g. 120) at BOTTOM
        t = (db - db_min) / db_range
        return margin_t + t * plot_h

    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)
    font = _try_font()
    small_font = _try_font((12, 11, 10))

    # ---- Grid ----
    # Light lines every 5 dB, heavy every 10 dB
    for db in range(db_min, db_max + 1, DB_STEP):
        y = db_to_y(db)
        heavy = (db % 10 == 0)
        color = COLOR_GRID_HEAVY if heavy else COLOR_GRID
        draw.line([margin_l, y, margin_l + plot_w, y], fill=color, width=2 if heavy else 1)

    # Vertical lines at each frequency
    for f in freqs:
        x = freq_to_x(f)
        draw.line([x, margin_t, x, margin_t + plot_h], fill=COLOR_GRID, width=1)

    # Axis borders
    draw.rectangle([margin_l, margin_t, margin_l + plot_w, margin_t + plot_h],
                   outline=COLOR_AXIS, width=2)

    # ---- Axis labels ----
    # Y axis (dB) — label every 10 dB
    for db in range(db_min, db_max + 1, 10):
        y = db_to_y(db)
        label = str(db)
        if font:
            draw.text((margin_l - 34, y - 8), label, fill=COLOR_AXIS, font=small_font)
        else:
            draw.text((margin_l - 34, y - 8), label, fill=COLOR_AXIS)

    # X axis (Hz) — label every frequency
    for f in freqs:
        x = freq_to_x(f)
        label = f"{f//1000}k" if f >= 1000 else str(f)
        w_est = 8 * len(label)
        if font:
            draw.text((x - w_est / 2, margin_t + plot_h + 8), label, fill=COLOR_AXIS, font=small_font)
        else:
            draw.text((x - w_est / 2, margin_t + plot_h + 8), label, fill=COLOR_AXIS)

    # Title
    if title and font:
        draw.text((width / 2 - 120, 20), title, fill=COLOR_AXIS, font=font)

    # ---- Symbols ----
    for i, f in enumerate(freqs):
        x = freq_to_x(f)
        if thresholds_right is not None and i < len(thresholds_right) and thresholds_right[i] is not None:
            draw_symbol(draw, x, db_to_y(thresholds_right[i]), SYMBOL_O, COLOR_RED)
        if thresholds_left is not None and i < len(thresholds_left) and thresholds_left[i] is not None:
            draw_symbol(draw, x, db_to_y(thresholds_left[i]), SYMBOL_X, COLOR_BLUE)
        if masked_right is not None and i < len(masked_right) and masked_right[i] is not None:
            draw_symbol(draw, x, db_to_y(masked_right[i]), SYMBOL_TRI, COLOR_RED)
        if masked_left is not None and i < len(masked_left) and masked_left[i] is not None:
            draw_symbol(draw, x, db_to_y(masked_left[i]), SYMBOL_SQ, COLOR_BLUE)

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path)
    return save_path


def demo_cases():
    """Return a few classic clinical cases with ground-truth values."""
    return {
        "normal": {
            "left": [10, 12, 15, 12, 14, 18, 20],
            "right": [8, 10, 12, 10, 12, 16, 18],
        },
        "noise_notch": {
            "left": [10, 12, 15, 35, 50, 55, 45],
            "right": [10, 12, 15, 40, 55, 60, 50],
        },
        "presbycusis": {
            "left": [15, 20, 30, 45, 60, 70, 75],
            "right": [15, 20, 30, 45, 60, 70, 75],
        },
        "asymmetric": {
            "left": [20, 25, 30, 35, 40, 45, 50],
            "right": [40, 45, 50, 55, 60, 65, 70],
        },
        "masked": {
            "left": [15, 20, 30, 45, 60, 70, 75],
            "right": [15, 20, 30, 45, 60, 70, 75],
            "masked_left": [None, None, None, None, 80, 90, None],
            "masked_right": [None, None, None, 70, 85, 95, None],
        },
    }


def generate_demo_images(outdir: str | Path = "demo_audiograms") -> dict[str, Path]:
    """Generate one image per demo case and return paths keyed by name."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, case in demo_cases().items():
        p = render_audiogram(
            thresholds_left=case.get("left"),
            thresholds_right=case.get("right"),
            masked_left=case.get("masked_left"),
            masked_right=case.get("masked_right"),
            title=f"Demo: {name.replace('_', ' ').title()}",
            save_path=outdir / f"{name}.png",
        )
        paths[name] = p
    return paths


if __name__ == "__main__":
    paths = generate_demo_images("/tmp/fa_demo")
    for name, p in paths.items():
        print(f"  {name}: {p}")
