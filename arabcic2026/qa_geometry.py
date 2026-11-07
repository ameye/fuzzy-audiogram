#!/usr/bin/env python3
"""Programmatic QA for a .pptx: text-frame geometry, overflow, images, style, word counts.

Measures every text frame against its box using real font metrics (Carlito is
metric-compatible with Calibri, Gelasio with Georgia), so overflow detection matches
what PowerPoint/LibreOffice will lay out rather than what looks fine on a laptop.

Usage:
  python3 deck_qa.py deck.pptx [--render OUTDIR] [--json out.json] [--quiet]

Exit code 1 if any hard failure (overflow, edge escape, mid-word break).
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Emu, Pt

FONTDIR = os.environ.get("DECK_QA_FONTS", "/opt/data/_fonts")
# Carlito is metric-compatible with Calibri and Gelasio with Georgia, so the
# measurements match PowerPoint layout. Drop the four Carlito faces and the
# Gelasio variable font in FONTDIR, then set DECK_QA_FONTS if it lives elsewhere.
EMU_PER_PT = 12700.0
EMU_PER_IN = 914400.0

# ---------------------------------------------------------------- font metrics
FONT_FILES = {
    ("calibri", False, False): "Carlito-Regular.ttf",
    ("calibri", True, False): "Carlito-Bold.ttf",
    ("calibri", False, True): "Carlito-Italic.ttf",
    ("calibri", True, True): "Carlito-BoldItalic.ttf",
}
SERIF = "Gelasio%5Bwght%5D.ttf"
_cache = {}


def _font(family, bold, italic, size_pt):
    fam = (family or "Calibri").strip().lower()
    key = (fam, bold, italic, size_pt)
    if key in _cache:
        return _cache[key]
    path = None
    if fam in ("georgia", "gelasio", "times new roman", "serif"):
        path = os.path.join(FONTDIR, SERIF)
    else:
        path = os.path.join(FONTDIR, FONT_FILES.get(
            ("calibri", bold, italic), "Carlito-Regular.ttf"))
    try:
        f = ImageFont.truetype(path, max(1, int(round(size_pt))))
        if "Gelasio" in path:
            try:
                f.set_variation_by_axes([700 if bold else 400])
            except Exception:
                pass
    except Exception:
        f = ImageFont.load_default()
    _cache[key] = f
    return f


def text_w(txt, family, bold, italic, size_pt):
    if not txt or not txt.strip():
        return 0.0
    try:
        return _font(family, bold, italic, size_pt).getlength(txt)
    except Exception:
        return 0.5 * size_pt * len(txt)


# ---------------------------------------------------------------- shape helpers
def emu_pt(v):
    return (v or 0) / EMU_PER_PT


def run_props(p, default_size=18.0):
    """(text, size, family, bold, italic) per run, falling back to paragraph defaults."""
    out = []
    for r in p.runs:
        size = r.font.size.pt if r.font.size is not None else (
            p.font.size.pt if p.font.size is not None else default_size)
        fam = r.font.name or p.font.name or "Calibri"
        bold = bool(r.font.bold if r.font.bold is not None else p.font.bold)
        ital = bool(r.font.italic if r.font.italic is not None else p.font.italic)
        out.append((r.text, size, fam, bold, ital))
    return out


def run_colour(p, default=(0x1B, 0x2A, 0x3A)):
    out = []
    for r in p.runs:
        try:
            c = r.font.color.rgb
            out.append(("#" + str(c)) if c else None)
        except Exception:
            out.append(None)
    return out


def para_metrics(p, width_pt, default_size=18.0):
    """Return (height_pt, lines, worst_line_width, unbreakable_word)."""
    runs = run_props(p, default_size)
    if not runs:
        size = p.font.size.pt if p.font.size is not None else default_size
        runs = [("", size, p.font.name or "Calibri", False, False)]
    max_size = max(r[1] for r in runs)
    ls = p.line_spacing
    line_mult = 1.0
    if isinstance(ls, float):
        line_mult = ls
    elif ls is not None:
        line_mult = 1.0  # exact spacing set in points
    # approximate a single line height: 1.2 * font size * multiplier
    line_h = 1.2 * max_size * line_mult

    # tokenise into words carrying their run style
    tokens = []  # (word_with_space, size, fam, bold, ital, is_break)
    for (t, size, fam, bold, ital) in runs:
        for chunk_i, chunk in enumerate(re.split(r"(\n)", t)):
            if chunk == "\n":
                tokens.append(("", size, fam, bold, ital, True))
                continue
            for piece in re.split(r"(\s+)", chunk):
                if piece == "":
                    continue
                tokens.append((piece, size, fam, bold, ital, False))

    lines, cur_w, worst, unbreakable = 1, 0.0, 0.0, ""
    for (tok, size, fam, bold, ital, forced) in tokens:
        if forced:
            worst = max(worst, cur_w)
            lines += 1
            cur_w = 0.0
            continue
        w = text_w(tok, fam, bold, ital, size)
        if tok.strip() and w > width_pt + 0.5:
            unbreakable = tok.strip()
        if tok.isspace():
            if cur_w > 0:
                cur_w += w
            continue
        if cur_w + w > width_pt + 0.2 and cur_w > 0:
            worst = max(worst, cur_w)
            lines += 1
            cur_w = w
        else:
            cur_w += w
    worst = max(worst, cur_w)

    sb = emu_pt(p.space_before) if p.space_before is not None else 0.0
    sa = emu_pt(p.space_after) if p.space_after is not None else 0.0
    return lines * line_h + sb + sa, lines, worst, unbreakable


def check_tf(shape, slide_w, slide_h, idx):
    tf = shape.text_frame
    txt = "".join(r.text for p in tf.paragraphs for r in p.runs).strip()
    if not txt:
        return None
    x, y = emu_pt(shape.left), emu_pt(shape.top)
    w, h = emu_pt(shape.width), emu_pt(shape.height)
    ml = emu_pt(tf.margin_left) if tf.margin_left is not None else 7.2
    mr = emu_pt(tf.margin_right) if tf.margin_right is not None else 7.2
    mt = emu_pt(tf.margin_top) if tf.margin_top is not None else 3.6
    mb = emu_pt(tf.margin_bottom) if tf.margin_bottom is not None else 3.6
    inner_w = max(1.0, w - ml - mr)
    inner_h = max(1.0, h - mt - mb)

    need = 0.0
    lines_total = 0
    unbreakable = ""
    worst_w = 0.0
    for p in tf.paragraphs:
        ph, lines, ww, ub = para_metrics(p, inner_w)
        need += ph
        lines_total += lines
        worst_w = max(worst_w, ww)
        if ub:
            unbreakable = ub

    res = dict(slide=idx, x=round(x / 72, 2), y=round(y / 72, 2),
               w=round(w / 72, 2), h=round(h / 72, 2),
               need_h=round(need / 72, 2), box_h=round(h / 72, 2),
               lines=lines_total, text=txt[:70], words=len(txt.split()),
               fill=round(100.0 * need / inner_h, 1))
    issues = []
    if need > inner_h + 0.5:
        issues.append("OVERFLOW")
    elif need > 0.93 * inner_h:
        issues.append("TIGHT")
    if x < -0.5 or y < -0.5 or x + w > slide_w + 0.5 or y + h > slide_h + 0.5:
        issues.append("OFFSLIDE")
    if unbreakable:
        issues.append("UNBREAKABLE")
        res["unbreakable_word"] = unbreakable
    # horizontal: a single word wider than the box means mid-word breaking
    res["issues"] = issues
    return res


def check_cell(cell, col_w_pt, row_h_pt):
    tf = cell.text_frame
    txt = tf.text.strip()
    if not txt:
        return None
    ml = emu_pt(cell.margin_left) if cell.margin_left is not None else 7.2
    mr = emu_pt(cell.margin_right) if cell.margin_right is not None else 7.2
    mt = emu_pt(cell.margin_top) if cell.margin_top is not None else 3.6
    mb = emu_pt(cell.margin_bottom) if cell.margin_bottom is not None else 3.6
    inner_w = max(1.0, col_w_pt - ml - mr)
    need = 0.0
    lines = 0
    worst = ""
    for p in tf.paragraphs:
        ph, ln, ww, ub = para_metrics(p, inner_w, default_size=11.0)
        need += ph
        lines += ln
        if ub:
            worst = ub
    return dict(text=txt[:40], need_h=round(need / 72, 2), row_h=round(row_h_pt / 72, 2),
                lines=lines, unbreakable=worst,
                over=need > (row_h_pt - mt - mb) + 0.5)


# ---------------------------------------------------------------- main audit
def audit(path):
    prs = Presentation(path)
    SW, SH = emu_pt(prs.slide_width), emu_pt(prs.slide_height)
    report = dict(file=path, slides=[], totals=dict(frames=0, overflow=0, tight=0,
                                                    offslide=0, unbreakable=0, cells_over=0,
                                                    lowdpi=0, slide_words=0, note_words=0))
    for i, slide in enumerate(prs.slides, 1):
        s = dict(n=i, shapes=len(slide.shapes), frames=[], cells=[], images=[],
                 slide_words=0, note_words=0)
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        s["note_words"] = len(notes.split())
        s["notes_chars"] = len(notes)
        s["has_notes"] = bool(notes)
        for sh in slide.shapes:
            if sh.has_text_frame:
                r = check_tf(sh, SW, SH, i)
                if r:
                    s["frames"].append(r)
                    s["slide_words"] += r["words"]
            if getattr(sh, "has_table", False) and sh.has_table:
                tbl = sh.table
                widths = [emu_pt(c.width) for c in tbl.columns]
                for ri, row in enumerate(tbl.rows):
                    rh = emu_pt(row.height)
                    for ci, cell in enumerate(row.cells):
                        c = check_cell(cell, widths[ci], rh)
                        if c:
                            c.update(row=ri, col=ci)
                            s["cells"].append(c)
            if sh.shape_type == 13:  # picture
                try:
                    disp_in = emu_pt(sh.width) / 72.0
                    px_w = sh.image.size[0]
                    s["images"].append(dict(px=sh.image.size, w_in=round(disp_in, 2),
                                            y_in=round(emu_pt(sh.top) / 72, 2),
                                            dpi=round(px_w / disp_in) if disp_in else 0))
                except Exception:
                    pass
        # slide word count from text frames (+ tables)
        tbl_words = sum(len(c["text"].split()) for c in s["cells"])
        s["slide_words"] += tbl_words
        s["table_words"] = tbl_words
        report["slides"].append(s)
        t = report["totals"]
        t["frames"] += len(s["frames"])
        t["overflow"] += sum("OVERFLOW" in f["issues"] for f in s["frames"])
        t["tight"] += sum("TIGHT" in f["issues"] for f in s["frames"])
        t["offslide"] += sum("OFFSLIDE" in f["issues"] for f in s["frames"])
        t["unbreakable"] += sum("UNBREAKABLE" in f["issues"] for f in s["frames"])
        t["cells_over"] += sum(c["over"] for c in s["cells"])
        t["lowdpi"] += sum(1 for im in s["images"] if im["dpi"] and im["dpi"] < 96)
        t["slide_words"] += s["slide_words"]
        t["note_words"] += s["note_words"]
    report["totals"]["slides"] = len(prs.slides)
    report["totals"]["talk_min_130wpm"] = round(report["totals"]["note_words"] / 130.0, 2)
    return report, prs


# ---------------------------------------------------------------- style audit
BRIT = {"analyze": "analyse", "analyzed": "analysed", "analyzing": "analysing",
        "characterize": "characterise", "characterized": "characterised",
        "optimize": "optimise", "optimized": "optimised", "optimizing": "optimising",
        "modeling": "modelling", "modeled": "modelled", "labeled": "labelled",
        "normalize": "normalise", "normalized": "normalised",
        "utilize": "utilise", "minimize": "minimise", "maximize": "maximise",
        "recognize": "recognise", "organize": "organise", "summarize": "summarise",
        "behavior": "behaviour", "color": "colour", "center": "centre",
        "pediatric": "paediatric", "defense": "defence", "liter": "litre",
        "program ": "programme ", "favor": "favour", "aging": "ageing",
        "catalog": "catalogue", "practiced": "practised"}


def style_audit(prs):
    hits = []
    for i, slide in enumerate(prs.slides, 1):
        texts = []
        for sh in slide.shapes:
            if sh.has_text_frame:
                texts.append(sh.text_frame.text)
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        texts.append(cell.text_frame.text)
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        for where, blob in (("slide", " \n".join(texts)), ("notes", notes)):
            for ch, name in (("\u2014", "em dash"), (";", "semicolon")):
                if ch in blob:
                    for m in re.finditer(re.escape(ch), blob):
                        hits.append(dict(slide=i, where=where, rule=name,
                                         ctx=blob[max(0, m.start() - 35):m.start() + 35].replace("\n", " ")))
            for m in re.finditer(":", blob):
                hits.append(dict(slide=i, where=where, rule="colon",
                                 ctx=blob[max(0, m.start() - 35):m.start() + 35].replace("\n", " ")))
            for bad, good in BRIT.items():
                pat = r"\b" + re.escape(bad.strip()) + (r"(?=\s)" if bad.endswith(" ") else "")
                for m in re.finditer(pat, blob, re.I):
                    hits.append(dict(slide=i, where=where, rule=f"US spelling {bad!r} -> {good!r}",
                                     ctx=blob[max(0, m.start() - 35):m.start() + 35].replace("\n", " ")))
    return hits


# ---------------------------------------------------------------- render preview
def render(prs, outdir, scale=1.6):
    os.makedirs(outdir, exist_ok=True)
    W, H = int(13.333 * 72 * scale), int(7.5 * 72 * scale)
    paths = []
    for i, slide in enumerate(prs.slides, 1):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        def S(v):  # pt -> px
            return v * scale
        for sh in slide.shapes:
            try:
                x, y = S(emu_pt(sh.left)), S(emu_pt(sh.top))
                w, h = S(emu_pt(sh.width)), S(emu_pt(sh.height))
            except Exception:
                continue
            if sh.shape_type == 13:
                try:
                    from io import BytesIO
                    im = Image.open(BytesIO(sh.image.blob))
                    im = im.convert("RGB").resize((max(1, int(w)), max(1, int(h))))
                    img.paste(im, (int(x), int(y)))
                except Exception:
                    d.rectangle([x, y, x + w, y + h], outline="#cccccc")
                continue
            fill = None
            try:
                if sh.fill.type == 1:
                    fill = "#" + str(sh.fill.fore_color.rgb)
            except Exception:
                fill = None
            if fill:
                try:
                    rounded = sh.adjustments[0] if len(sh.adjustments) else 0
                except Exception:
                    rounded = 0
                if rounded and sh.shape_type == 5:
                    d.rounded_rectangle([x, y, x + w, y + h], radius=max(2, rounded * min(w, h)),
                                        fill=fill)
                else:
                    d.rectangle([x, y, x + w, y + h], fill=fill)
            if getattr(sh, "has_table", False) and sh.has_table:
                tbl = sh.table
                widths = [S(emu_pt(c.width)) for c in tbl.columns]
                cy = y
                for row in tbl.rows:
                    rh = S(emu_pt(row.height))
                    cx = x
                    for ci, cell in enumerate(row.cells):
                        try:
                            cf = "#" + str(cell.fill.fore_color.rgb) if cell.fill.type == 1 else "#ffffff"
                        except Exception:
                            cf = "#ffffff"
                        d.rectangle([cx, cy, cx + widths[ci], cy + rh], fill=cf, outline="#dde3ea")
                        if cell.text_frame.text.strip():
                            d.text((cx + 4, cy + 4), cell.text_frame.text.strip()[:40],
                                   fill="black", font=_font("Calibri", False, False, int(9 * scale)))
                        cx += widths[ci]
                    cy += rh
            if sh.has_text_frame and sh.text_frame.text.strip():
                tf = sh.text_frame
                ml = S(emu_pt(tf.margin_left or 0)); mt = S(emu_pt(tf.margin_top or 0))
                inner_w = w - ml - S(emu_pt(tf.margin_right or 0))
                cy = y + mt
                for p in tf.paragraphs:
                    runs = run_props(p)
                    if not runs:
                        continue
                    # simple wrap
                    words = []
                    for (t, size, fam, bold, ital) in runs:
                        for piece in re.split(r"(\s+)", t):
                            if piece:
                                words.append((piece, size, fam, bold, ital))
                    cs = run_colour(p)
                    line_col = cs[0] if cs and cs[0] else None
                    cur = []  # list of (text,size,fam,bold,ital)
                    cur_w = 0.0
                    maxsize = max(r[1] for r in runs)

                    def flush(line):
                        nonlocal cy
                        line_w = sum(text_w(t, fam, bold, ital, size * scale)
                                     for (t, size, fam, bold, ital) in line)
                        lx = x + ml
                        try:
                            al = p.alignment
                        except Exception:
                            al = None
                        if al is not None and int(al) == 2:      # centre
                            lx = x + ml + max(0.0, (inner_w - line_w) / 2)
                        elif al is not None and int(al) == 3:    # right
                            lx = x + ml + max(0.0, inner_w - line_w)
                        for (t, size, fam, bold, ital) in line:
                            f = _font(fam, bold, ital, int(size * scale))
                            if t.strip():
                                d.text((lx, cy), t, fill=line_col or "black", font=f)
                            lx += text_w(t, fam, bold, ital, size * scale)
                        cy += maxsize * scale * 1.22

                    for wd in words:
                        wl = text_w(wd[0], wd[2], wd[3], wd[4], wd[1] * scale)
                        if cur and cur_w + wl > inner_w:
                            flush(cur)
                            cur, cur_w = [], 0.0
                        if wd[0].isspace():
                            cur.append(wd)
                            cur_w += wl
                        else:
                            cur.append(wd)
                            cur_w += wl
                    if cur:
                        flush(cur)
            if sh.has_text_frame and len(sh.text_frame.paragraphs) and \
               sh.text_frame.vertical_anchor == 3 and sh.text_frame.text.strip():
                pass
        # notes marker + slot number
        d.text((10, H - 22), f"slide {i}", fill="#888888", font=_font("Calibri", False, False, 12))
        p = os.path.join(outdir, f"slide-{i:02d}.png")
        img.save(p)
        paths.append(p)
    return paths


def main():
    argv = sys.argv[1:]
    flags = []
    args = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            flags.append(a)
            if a in ("--render", "--json"):
                flags.append(argv[i + 1])
                i += 1
        else:
            args.append(a)
        i += 1
    path = args[0]
    report, prs = audit(path)
    style = style_audit(prs)
    if "--render" in flags:
        outdir = flags[flags.index("--render") + 1]
        render(prs, outdir)
    if "--json" in flags:
        with open(flags[flags.index("--json") + 1], "w") as fh:
            json.dump(dict(report=report, style=style), fh, indent=1)

    t = report["totals"]
    print(f"FILE {path}")
    print(f"slides={t['slides']} text_frames={t['frames']} overflow={t['overflow']} "
          f"tight={t['tight']} offslide={t['offslide']} unbreakable={t['unbreakable']} "
          f"cells_over={t['cells_over']} lowdpi={t['lowdpi']}")
    print(f"words on slide={t['slide_words']} notes={t['note_words']} "
          f"talk={t['talk_min_130wpm']} min @130wpm")
    print("-" * 100)
    for s in report["slides"]:
        bad = [f for f in s["frames"] if f["issues"]]
        cbad = [c for c in s["cells"] if c["over"]]
        imgs = " ".join(f"{im['px'][0]}px/{im['w_in']}in={im['dpi']}dpi" for im in s["images"])
        flag = "OK " if not (bad or cbad) else "!! "
        print(f"{flag}p{s['n']:>2} words={s['slide_words']:>3} notes={s['note_words']:>3} "
              f"frames={len(s['frames']):>2} bad={len(bad):>2} cells_over={len(cbad)} {imgs}")
        for f in bad:
            print(f"      {'/'.join(f['issues'])} box({f['x']},{f['y']},{f['w']}x{f['h']}) "
                  f"need={f['need_h']}in fill={f['fill']}% :: {f['text'][:60]!r}")
        for c in cbad:
            print(f"      CELL r{c['row']}c{c['col']} need={c['need_h']} row={c['row_h']} :: {c['text'][:50]!r}")
    print("-" * 100)
    if style:
        print(f"STYLE HITS {len(style)}")
        for h in style:
            print(f"  p{h['slide']} {h['where']} {h['rule']}: ...{h['ctx']}...")
    else:
        print("STYLE HITS 0")
    hard = t["overflow"] + t["offslide"] + t["unbreakable"] + t["cells_over"]
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
