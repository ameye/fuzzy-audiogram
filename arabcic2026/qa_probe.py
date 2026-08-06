#!/usr/bin/env python3
"""Programmatic QA of the rendered deck PDF: page bounds, text-text collisions, image embeds."""
import sys
sys.path.insert(0, '/home/hermes/.hermes/home/.local/lib/python3.13/site-packages')
import fitz

doc = fitz.open("/opt/data/fuzzy-audiogram/arabcic2026/qa/arabcic2026_fuzzy_audiogram.pdf")
PW, PH = 960.0, 540.0  # 13.333x7.5 in @72pt
issues = []
for pno, page in enumerate(doc, 1):
    r = page.rect
    blocks = [b for b in page.get_text("blocks") if b[6] == 0]  # text blocks
    # 1. page-edge overflow (allow 6pt breathing room)
    for b in blocks:
        x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4].strip().replace("\n", " ")
        if x1 > r.width - 4 or y1 > r.height - 4 or x0 < 4 or y0 < 4:
            issues.append(f"p{pno} EDGE: ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) '{text[:60]}'")
    # 2. text-text collisions (significant overlap of two text blocks)
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            a, b = blocks[i], blocks[j]
            ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            inter = ix * iy
            if inter <= 0:
                continue
            area_a = (a[2] - a[0]) * (a[3] - a[1])
            area_b = (b[2] - b[0]) * (b[3] - b[1])
            if inter > 0.35 * min(area_a, area_b):
                issues.append(
                    f"p{pno} COLLIDE: '{a[4].strip()[:38]}' <-> '{b[4].strip()[:38]}' "
                    f"inter={inter:.0f}")
    # 3. image embeds per page
    n_img = len(page.get_image_info())
    print(f"page {pno}: {len(blocks)} text blocks, {n_img} image(s)")
print("\n--- ISSUES ---")
if not issues:
    print("none")
for it in issues:
    print(it)
