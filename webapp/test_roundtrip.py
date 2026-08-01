"""Round-trip test: render audiogram -> OCR -> compare with ground truth."""
import sys
sys.path.insert(0, "/workspace/fuzzy-audiogram/webapp")

from services.audiogram_renderer import generate_demo_images, demo_cases
from services.audiogram_ocr import AudiogramOCR

paths = generate_demo_images("/tmp/fa_demo")
ocr = AudiogramOCR()

print("=" * 70)
for name, case in demo_cases().items():
    p = paths[name]
    res = ocr.extract(p)

    gt_left = case.get("left") or []
    gt_right = case.get("right") or []
    ocr_left = res.thresholds_left
    ocr_right = res.thresholds_right

    print(f"\n### {name} — image: {p.name}")
    print(f"  Calibration: {res.calibration}")
    print(f"  Warnings: {res.warnings}")

    # Compare on framework frequencies
    freqs = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
    gt_by_freq_l = dict(zip([125, 250, 500, 1000, 2000, 4000, 8000], gt_left)) if gt_left else {}
    gt_by_freq_r = dict(zip([125, 250, 500, 1000, 2000, 4000, 8000], gt_right)) if gt_right else {}

    print(f"  LEFT  OCR: {ocr_left}")
    print(f"  LEFT  GT : {gt_by_freq_l}")
    print(f"  RIGHT OCR: {ocr_right}")
    print(f"  RIGHT GT : {gt_by_freq_r}")
    print(f"  Symbols: {len(res.symbols)}")

    # Accuracy: compare where both exist
    errs = []
    for freq, gt in gt_by_freq_l.items():
        if freq in ocr_left:
            errs.append(abs(ocr_left[freq] - gt))
    for freq, gt in gt_by_freq_r.items():
        if freq in ocr_right:
            errs.append(abs(ocr_right[freq] - gt))
    if errs:
        print(f"  Mean abs error: {sum(errs)/len(errs):.1f} dB over {len(errs)} points")
    else:
        print("  ⚠️ No matching points to compare")
