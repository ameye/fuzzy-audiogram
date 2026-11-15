"""Build the infographic panels for EDA_VISUAL_REPORT.md.

These are not analysis figures: every number they carry is copied from
EDA_REPORT.md and none is recomputed. Each panel is drawn as SVG in pixel
units at 300 dpi and rasterised with cairosvg, so the result is a 300 dpi
PNG whose width matches the A4 text block used by build_visual_pdf.py.

All vertical layout is in pixels at 300 dpi and every block returns the y it
finished at, so nothing is positioned against a guessed height. Text is
measured with the same TTF files cairo renders, so widths and wraps agree
with the output.

Usage:  python make_visuals.py
        VIS_OUT=../visual python make_visuals.py
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PIL import ImageFont

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("VIS_OUT", HERE / "visual"))
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- palette
INK = "#17171B"
BODY = "#2E2E36"
MUTED = "#5E5E68"
RULE = "#D3D3DB"
PAPER = "#FFFFFF"
PANEL = "#F5F3EC"

FIND = "#1F6F6B"
FIND_T = "#E6EFED"
PROB = "#9B2C3F"
PROB_T = "#F7E8EB"
FIX = "#55731F"
FIX_T = "#EDF1E0"
QUERY = "#A86B22"
QUERY_T = "#F8EEDE"
REVIEW = "#35526E"
REVIEW_T = "#E6EBF1"
LIMIT = "#5E5E68"
LIMIT_T = "#ECECEE"

FONT = "DejaVu Sans"
SERIF = "DejaVu Serif"
S = 300 / 72.0            # px per pt at 300 dpi
W = 2031                  # 17.2 cm at 300 dpi
PAD = 28                  # inner margin: text never starts on the canvas edge

_FP = {
    ("sans", False): "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ("sans", True): "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ("serif", False): "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ("serif", True): "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
}
_cache: dict = {}
WARN: list[str] = []


def _font(size_pt, bold=False, family="sans"):
    key = (size_pt, bold, family)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(_FP[(family, bold)], int(round(size_pt * S)))
    return _cache[key]


def tw(s, size_pt, bold=False, family="sans"):
    return _font(size_pt, bold, family).getlength(s)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cap(size_pt):
    return size_pt * S * 0.72


def lh(size_pt, lead=1.2):
    return size_pt * S * lead


class Canvas:
    def __init__(self, h, w=W, bg=PAPER):
        self.w, self.h, self.bg = w, h, bg
        self.parts = []

    # ---------------------------------------------------------- atoms
    def rect(self, x, y, w, h, fill="none", stroke="none", sw=1, rx=0, dash=None, op=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op}"/>')

    def line(self, x1, y1, x2, y2, stroke=RULE, sw=1, dash=None, op=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d} opacity="{op}"/>')

    def path(self, d, fill="none", stroke="none", sw=1, op=1.0, dash=None):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
                          f'stroke-width="{sw}" opacity="{op}"{ds}/>')

    def text(self, x, y, s, size=9, fill=INK, bold=False, anchor="start", family="sans", op=1.0):
        fam = FONT if family == "sans" else SERIF
        wt = ' font-weight="bold"' if bold else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" '
            f'font-size="{size * S:.1f}" fill="{fill}" text-anchor="{anchor}"{wt} '
            f'opacity="{op}">{esc(s)}</text>')

    def text_top(self, x, top, s, size=9, fill=INK, bold=False, anchor="start", family="sans"):
        self.text(x, top + size * S * 0.82, s, size, fill, bold, anchor, family)

    def tracked(self, x, top, s, size=7.2, fill=MUTED, bold=True, track=0.17, anchor="start"):
        s = s.upper()
        gap = track * size * S
        widths = [tw(ch, size, bold) for ch in s]
        total = sum(widths) + gap * max(0, len(s) - 1)
        if anchor == "middle":
            x -= total / 2
        elif anchor == "end":
            x -= total
        cx = x
        for ch, wch in zip(s, widths):
            self.text(cx, top + size * S * 0.82, ch, size, fill, bold)
            cx += wch + gap
        return total

    def wrap(self, s, size, maxw, bold=False, family="sans"):
        words, lines, cur = s.split(), [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if tw(trial, size, bold, family) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, top, s, size, maxw, fill=BODY, lead=1.42, bold=False, family="sans"):
        lines = self.wrap(s, size, maxw, bold, family)
        for i, ln in enumerate(lines):
            if tw(ln, size, bold, family) > maxw + 1:
                WARN.append(f"overflow {size}pt: {ln[:38]!r}")
            self.text_top(x, top + i * lh(size, lead), ln, size, fill, bold, "start", family)
        return top + (len(lines) - 1) * lh(size, lead) + size * S * 1.15

    # ------------------------------------------------------- composites
    def fit_numeral(self, numeral, w, numsize):
        s = numsize
        while tw(numeral, s, True) > w - 60 and s > 20:
            s -= 2
        return s

    def card(self, x, top, w, h, numeral, label, note, colour, tint, numsize=46, notepts=9.8):
        """Stat card. Height is given so a row can share one height."""
        numsize = self.fit_numeral(numeral, w, numsize)
        self.rect(x, top, w, h, fill=tint)
        self.rect(x, top, w, 6, fill=colour)
        ny = top + 38
        self.text(x + 28, ny + cap(numsize), numeral, numsize, colour, True)
        ly = ny + cap(numsize) + 26
        self.tracked(x + 30, ly, label, 7.0, INK, True, 0.13)
        self.para(x + 30, ly + lh(7.0, 1.2) + 14, note, notepts, w - 58, MUTED, 1.42)
        return top + h

    def card_h(self, numeral, label, note, w, numsize=46, notepts=9.8):
        numsize = self.fit_numeral(numeral, w, numsize)
        nl = len(self.wrap(note, notepts, w - 58))
        return (38 + cap(numsize) + 26 + lh(7.0, 1.2) + 14
                + nl * lh(notepts, 1.42) + 34)

    def box(self, x, top, w, h, title, subs=(), colour=INK, tint=PAPER, sw=2,
            tsize=10.4, dash=None, big=None, bigsize=30):
        """Bordered panel. Text is placed from the top, never centred."""
        self.rect(x, top, w, h, fill=tint, stroke=colour, sw=sw, dash=dash)
        y = top + 26
        if big:
            self.text(x + 22, y + cap(bigsize), big, bigsize, colour, True)
            y += cap(bigsize) + 18
        self.text_top(x + 22, y, title, tsize, colour, True)
        y += lh(tsize, 1.2) + 6
        for sub in subs:
            self.text_top(x + 22, y, sub, 8.0, MUTED)
            y += lh(8.0, 1.25)
        for sub in subs:
            if tw(sub, 8.0) > w - 44:
                WARN.append(f"box sub overflow: {sub!r} in {w}px")
        return top + h

    def arrow(self, x1, y, x2, colour=MUTED, sw=2.2):
        self.line(x1, y, x2 - 9, y, colour, sw)
        self.path(f"M {x2 - 11:.1f} {y - 7:.1f} L {x2:.1f} {y:.1f} L {x2 - 11:.1f} {y + 7:.1f} Z",
                  fill=colour)

    def down_arrow(self, x, y1, y2, colour=MUTED, sw=2.2):
        self.line(x, y1, x, y2 - 9, colour, sw)
        self.path(f"M {x - 7:.1f} {y2 - 11:.1f} L {x:.1f} {y2:.1f} L {x + 7:.1f} {y2 - 11:.1f} Z",
                  fill=colour)

    def save(self, name, trim=True):
        if trim:
            self.h = int(max(self._max_y, 10))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
               f'height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
               f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>'
               + "".join(self.parts) + "</svg>")
        sp = OUT / f"{name}.svg"
        sp.write_text(svg, encoding="utf-8")
        png = OUT / f"{name}.png"
        subprocess.run(["/home/hermes/.hermes/home/.local/bin/cairosvg", str(sp),
                        "-o", str(png), "--output-width", str(self.w)],
                       check=True, capture_output=True)
        print(f"{name}: {self.w}x{self.h} px  "
              f"({self.w / 300 * 2.54:.1f} x {self.h / 300 * 2.54:.1f} cm)")
        return png

    _max_y = 0


# =====================================================================
def p01_summary():
    gapx = 40
    cw = (W - 2 * PAD - 2 * gapx) / 3
    m = Canvas(10)

    row1 = [
        ("410", "ears in the analysis",
         "205 patients, 205 left and 205 right. Nothing is missing on age, sex "
         "or side, and all six grades hold at least 47 ears.", FIND, FIND_T),
        ("0.947", "kappa against Clark",
         "On the 390 ears the frozen index can grade. Exact agreement 69.5%, "
         "unweighted kappa 0.632.", FIND, FIND_T),
        ("57.6%", "within 5 dB of a cut",
         "236 of 410 ears. A sample built on the boundary rather than on clear "
         "cases, which is what a validation sample needs.", FIND, FIND_T),
    ]
    row2 = [
        ("20", "ears ungraded",
         "4.9% of the sample. Sixteen raise on shape, four on severity, and they "
         "are the worst-hearing ears.", PROB, PROB_T),
        ("100%", "consultant grade filled",
         "The protocol says blank unless documented. This field is the reference "
         "standard for Objective 2.", PROB, PROB_T),
        ("2", "schemes in play",
         "Six grades in the protocol, five in the shipped script. Running it "
         "answers a different question.", PROB, PROB_T),
    ]
    h1 = max(m.card_h(n, l, t, cw) for n, l, t, _, _ in row1)
    h2 = max(m.card_h(n, l, t, cw) for n, l, t, _, _ in row2)

    top = 46
    h1y = top + 40
    h2y = h1y + h1 + 72
    strip_y = h2y + h2 + 40
    strip_h = 176

    verdict = ("The sample is fit for purpose: large, well spread across grades, and "
               "unusually rich in boundary cases. Three fixes get it to submission. "
               "Repair the index crash, correct the batch script's grading scheme, and "
               "establish whether the consultant grade and documented shape were "
               "transcribed or inferred.")
    vlines = m.wrap(verdict, 14.0, W - 130, False, "serif")
    vh = 70 + len(vlines) * lh(14.0, 1.50) + 40
    vy = strip_y + strip_h + 34

    foot = ("Every number here is taken unchanged from EDA_REPORT.md. Agreement statistics "
            "rest on the 390 ears the frozen index classifies, and the 20 failures are "
            "reported as a finding rather than repaired. Section 7 sets out what changes "
            "once they are.")
    flines = m.wrap(foot, 9.0, W)
    foot_y = vy + vh + 44
    total = int(foot_y + 28 + len(flines) * lh(9.0, 1.45) + 30)

    c = Canvas(total)
    c.tracked(PAD, top, "the whole study, in six numbers", 7.2, PROB, True, 0.22)

    for i, (n, l, t, col, tint) in enumerate(row1):
        c.card(PAD + i * (cw + gapx), h1y, cw, h1, n, l, t, col, tint)

    c.tracked(PAD, h1y + h1 + 38, "and the three defects standing in the way", 7.2, PROB, True, 0.22)
    for i, (n, l, t, col, tint) in enumerate(row2):
        c.card(PAD + i * (cw + gapx), h2y, cw, h2, n, l, t, col, tint)

    c.line(0, strip_y, W, strip_y, RULE, 2)
    chips = [
        ("median age", "60", "IQR 41–72"),
        ("sex", "158 / 252", "male / female"),
        ("collection", "11 runs", "40 of 78 months"),
        ("2023", "0 ears", "a year missing"),
        ("diagnosis", "44.1%", "rest residual"),
    ]
    xw = (W - 2 * PAD) / len(chips)
    for i, (lab, val, sub) in enumerate(chips):
        cx = PAD + i * xw
        if i:
            c.line(cx - 30, strip_y + 28, cx - 30, strip_y + strip_h - 34, RULE, 2)
        c.tracked(cx, strip_y + 30, lab, 6.4, MUTED, True, 0.16)
        c.text_top(cx, strip_y + 58, val, 15, INK, True)
        c.text_top(cx, strip_y + 58 + lh(15, 1.25), sub, 8.2, MUTED)
    c.line(0, strip_y + strip_h, W, strip_y + strip_h, RULE, 2)

    c.rect(0, vy, W, vh, fill=PANEL)
    c.rect(0, vy, 8, vh, fill=FIND)
    c.tracked(44, vy + 30, "bottom line", 7.2, FIND, True, 0.2)
    c.para(44, vy + 70, verdict, 14.0, W - 130, BODY, 1.50, False, "serif")

    c.line(0, foot_y, W, foot_y, RULE, 2)
    c.para(PAD, foot_y + 26, foot, 9.0, W - 2 * PAD, MUTED, 1.45)
    c._max_y = total - 24
    return c.save("p01_summary", trim=False)


# =====================================================================
def p02_pipeline():
    bw, gp = (W - 2 * PAD - 3 * 76) / 4, 76
    xs = [PAD + k * (bw + gp) for k in range(4)]

    def box_h(subs, big=None, tsize=10.2, bigsize=30):
        h = 26
        if big:
            h += cap(bigsize) + 18
        h += lh(tsize, 1.2) + 6 + len(subs) * lh(8.0, 1.25) + 26
        return h

    h1 = max(box_h(("raw_export.csv",), big="410"), box_h(()),
             box_h(("of 410",), big="390"), box_h(("sections 6.3 to 6.6",)))
    h2 = max(box_h(("16 no shape rule", "4 no severity rule"), big="20"),
             box_h(("FAI 0.3.1, all 410 ears", "not the run described here")))

    y1 = 100
    y2 = y1 + h1 + 46

    c = Canvas(int(y2 + h2 + 190))
    c.tracked(PAD, 18, "from export to agreement table", 7.2, MUTED, True, 0.22)

    c.box(xs[0], y1, bw, h1, "ear records", ("raw_export.csv",), INK, PAPER, 2, 10.2, big="410")
    c.box(xs[1], y1, bw, h1, "frozen index", ("FAI 0.3.0", "rule base as shipped"),
          INK, PAPER, 2, 10.2)
    c.box(xs[2], y1, bw, h1, "ears graded", ("of 410",), FIND, FIND_T, 2, 10.2, big="390")
    c.box(xs[3], y1, bw, h1, "agreement tables", ("sections 6.3 to 6.6",),
          FIND, FIND_T, 2, 10.2)

    mid = y1 + h1 / 2
    c.arrow(xs[0] + bw + 10, mid, xs[1] - 6)
    c.arrow(xs[1] + bw + 10, mid, xs[2] - 6)
    c.arrow(xs[2] + bw + 10, mid, xs[3] - 6)

    # the branch: 20 ears leave the main line and are recovered separately
    c.down_arrow(xs[1] + bw / 2, y1 + h1 + 6, y2 - 6, PROB)
    c.box(xs[1], y2, bw, h2, "refused", ("16 no shape rule", "4 no severity rule"),
          PROB, PROB_T, 2, 10.2, big="20")
    c.arrow(xs[1] + bw + 10, y2 + h2 / 2, xs[2] - 6, PROB)

    c.rect(xs[2], y2, bw, h2, fill=FIX_T, stroke=FIX, sw=2, dash="12 8")
    c.text_top(xs[2] + 22, y2 + 26, "410 graded", 12.4, FIX, True)
    c.text_top(xs[2] + 22, y2 + 26 + lh(12.4, 1.2) + 8,
               "FAI 0.3.1, all 410 ears", 7.7, MUTED)
    c.text_top(xs[2] + 22, y2 + 26 + lh(12.4, 1.2) + lh(7.7, 1.3) + 8,
               "not the run described here", 7.7, MUTED)

    ry_ = y2 + h2 + 34
    c.line(0, ry_, W, ry_, RULE, 2)
    end = c.para(PAD, ry_ + 26,
                 "The frozen index raises on 20 ears because no rule fires for an optional "
                 "consequent and the key is then read unconditionally. That is an implementation "
                 "defect, not a data defect. This report takes the honest route: 410 ears for "
                 "the descriptive work, n = 390 for agreement, and the 20 failures stated "
                 "rather than quietly patched. Do not mix the two runs.", 9.2, W, BODY, 1.48)
    c._max_y = end + 24
    return c.save("p02_pipeline")


# =====================================================================
def p03_schemes():
    top, hgt = 132, 690
    k = hgt / 410.0
    LX, LW = 560, 150
    RX, RW = 1450, 150

    c = Canvas(1200)
    c.tracked(LX, 14, "six grades, 25/40/55/70/90", 7.2, FIND, True, 0.16)
    c.text_top(LX, 36, "protocol and Clark", 8.4, MUTED)
    c.tracked(RX, 14, "five grades, 25/40/60/80", 7.2, QUERY, True, 0.16)
    c.text_top(RX, 36, "shipped batch script", 8.4, MUTED)

    six = [("normal", 95, "25"), ("mild", 65, "40"), ("moderate", 70, "55"),
           ("moderately severe", 79, "70"), ("severe", 54, "90"), ("profound", 47, None)]
    five = [("normal", 95, "25"), ("mild", 65, "40"), ("moderate", 95, "60"),
            ("severe", 93, "80"), ("profound", 62, None)]

    ly, ry = {}, {}
    y = top
    for lab, n, cut in six:
        h = n * k
        ly[lab] = (y, h)
        c.rect(LX, y, LW, h, fill="#F1F0EA", stroke=INK, sw=1.5)
        c.text(LX - 74, y + h / 2 + 4, f"{lab}  {n}", 8.4, INK, True, "end")
        if cut:
            c.line(LX - 30, y + h, LX - 8, y + h, MUTED, 1.1, "5 5")
            c.text(LX - 34, y + h + 4, cut, 7.2, MUTED, False, "end")
        y += h

    y = top
    for lab, n, cut in five:
        h = n * k
        ry[lab] = (y, h)
        c.rect(RX, y, RW, h, fill=QUERY_T, stroke=QUERY, sw=1.5)
        c.text(RX + RW + 74, y + h / 2 + 4, f"{lab}  {n}", 8.8, INK, True)
        if cut:
            c.line(RX + RW + 8, y + h, RX + RW + 30, y + h, MUTED, 1.1, "5 5")
            c.text(RX + RW + 34, y + h + 4, cut, 7.2, MUTED)
        y += h

    msy, msh = ly["moderately severe"]
    c.path(
        f"M {LX + LW} {msy} C 950 {msy} 1050 {ry['moderate'][0] + ry['moderate'][1] - 25 * k} "
        f"{RX} {ry['moderate'][0] + ry['moderate'][1] - 25 * k} "
        f"L {RX} {ry['moderate'][0] + ry['moderate'][1]} "
        f"C 1050 {ry['moderate'][0] + ry['moderate'][1]} 950 {msy + 25 * k} "
        f"{LX + LW} {msy + 25 * k} Z", fill=PROB, op=0.16)
    c.text(1080, msy - 14, "25 to moderate", 8.8, PROB, True, "middle")

    c.path(
        f"M {LX + LW} {msy + 25 * k} C 950 {msy + 25 * k} 1050 {ry['severe'][0]} {RX} {ry['severe'][0]} "
        f"L {RX} {ry['severe'][0] + 54 * k} "
        f"C 1050 {ry['severe'][0] + 54 * k} 950 {msy + msh} {LX + LW} {msy + msh} Z",
        fill=PROB, op=0.24)
    c.text(1080, msy + 104, "54 to severe", 8.8, PROB, True, "middle")

    sy_, sh = ly["severe"]
    c.path(
        f"M {LX + LW} {sy_} C 950 {sy_} 1050 {ry['profound'][0] + 47 * k} {RX} {ry['profound'][0] + 47 * k} "
        f"L {RX} {ry['profound'][0] + 62 * k} "
        f"C 1050 {ry['profound'][0] + 62 * k} 950 {sy_ + 15 * k} {LX + LW} {sy_ + 15 * k} Z",
        fill=QUERY, op=0.32)
    c.text(1240, sy_ + 58, "15 to profound", 8.8, PROB, True, "middle")

    by = top + hgt + 56
    c.line(0, by - 28, W, by - 28, RULE, 2)
    c.text(PAD, by + cap(34), "79", 34, PROB, True)
    c.text_top(PAD + 232, by + 6, "ears sit in the band the five-grade scheme does not define.",
               11.6, INK, True)
    end = c.para(PAD, by + cap(34) + 18,
                 "Of those, 25 fall to moderate and 54 to severe. A further 15 ears that Clark "
                 "calls severe move up to profound. 94 ears, 22.9% of the sample, change grade "
                 "on a definitional choice alone. Nothing clinical separates the two columns: "
                 "only where the cuts fall.", 9.4, W, MUTED, 1.45)
    c._max_y = end + 26
    return c.save("p03_schemes")


# =====================================================================
def p04_calendar():
    left, right = 170, 24
    gap = 6
    cw = (W - left - right - gap * 11) / 12
    ch, rgap = 66, 8
    top = 92

    runs = {
        2020: {2: 1, 3: 1, 7: 2, 8: 2, 9: 2, 10: 2, 11: 2, 12: 2},
        2021: {1: 2, 3: 3, 4: 3, 5: 3, 6: 3, 11: 4, 12: 4},
        2022: {1: 4, 2: 4, 5: 5, 8: 6, 9: 6, 10: 6, 11: 6, 12: 6},
        2023: {},
        2024: {m: 7 for m in range(1, 8)},
        2025: {2: 8, 3: 8, 4: 8, 5: 8, 7: 9, 8: 9, 10: 10},
        2026: {4: 11, 5: 11, 6: 11},
    }
    first = {}
    for yr, mm in runs.items():
        for m, r in mm.items():
            first.setdefault(r, (yr, m))

    c = Canvas(900)
    c.tracked(PAD, 14, "78 months in the window, 40 with a record", 7.2, MUTED, True, 0.22)

    for m, name in enumerate(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]):
        c.text(left + m * (cw + gap) + cw / 2, top - 12, name, 7.2, MUTED, True, "middle")

    for yr in range(2020, 2027):
        y = top + (yr - 2020) * (ch + rgap)
        c.text(left - 24, y + ch / 2 + 5, str(yr), 9.8,
               INK if yr != 2023 else PROB, True, "end")
        if yr == 2023:
            c.text(left - 24, y + ch / 2 + 26, "empty", 7.4, PROB, False, "end")
        for m in range(1, 13):
            x = left + (m - 1) * (cw + gap)
            if yr == 2023:
                c.rect(x, y, cw, ch, fill=PROB_T, stroke=PROB, sw=1.2, dash="7 6")
                continue
            if yr == 2026 and m > 6:
                c.rect(x, y, cw, ch, fill="#F3F3F5", stroke=RULE, sw=1, dash="3 5")
                if m == 7:
                    c.text_top(x + 10, y + ch / 2 - 14, "outside", 6.8, MUTED)
                    c.text_top(x + 10, y + ch / 2 + 4, "window", 6.8, MUTED)
                continue
            r = runs[yr].get(m)
            if r:
                c.rect(x, y, cw, ch, fill=FIND, stroke=FIND, sw=1)
                if first[r] == (yr, m):
                    c.text(x + 10, y + 22, f"R{r}", 7.6, "#DCE9E6", True)
                else:
                    c.rect(x + cw - 20, y + 7, 12, 12, fill="#DCE9E6", op=0.5)
            else:
                c.rect(x, y, cw, ch, fill=PAPER, stroke="#C8C8D0", sw=1.1, dash="4 5")

    y23 = top + 3 * (ch + rgap)
    c.text(left + 6 * (cw + gap) - 30, y23 + ch / 2 + 4, "no records in 2023", 9.2, PROB, True, "middle")

    ly = top + 7 * (ch + rgap) + 40
    x = 0
    for col, kind, lab in [(FIND, "run", "month inside an extraction run"),
                           (PAPER, "empty", "month with no record"),
                           (PROB_T, "gap", "2023, entirely absent")]:
        if kind == "empty":
            c.rect(x, ly - 20, 22, 22, fill=PAPER, stroke="#C8C8D0", sw=1.1, dash="4 5")
        else:
            c.rect(x, ly - 20, 22, 22, fill=col, stroke=PROB if kind == "gap" else col, sw=1.2)
        c.text_top(x + 32, ly - 18, lab, 8.2, MUTED)
        x += 32 + tw(lab, 8.2) + 48

    ry_ = ly + 34
    c.line(0, ry_, W, ry_, RULE, 2)
    c.text(PAD, ry_ + 46 + cap(24), "11", 24, INK, True)
    c.text_top(PAD + 160, ry_ + 38, "contiguous runs, not one consecutive series.", 10.0, INK, True)
    end = c.para(PAD, ry_ + 46 + cap(24) + 14,
                 "Run sizes range from 2 to 94 ears (SD 32) and five months sit at exactly 22. "
                 "40 of 78 months carry records (51.3%). This is batch extraction to a target, "
                 "and the protocol's claim of consecutive sampling does not survive it.",
                 9.2, W, MUTED, 1.45)
    c._max_y = end + 24
    return c.save("p04_calendar")


# =====================================================================
def p05_triage():
    cols = [
        ("QUERY", "back to the data collector", PROB, PROB_T, "?", [], [
            ("consultant_grade 100% populated", "410 of 410",
             "Verify it was transcribed, not inferred."),
            ("documented_shape 99.8%", "409 of 410",
             "Same question, lower stakes. Study 257 blank."),
            ("Zero exclusions applied", "410 of 410",
             "No exclusion reason anywhere. Never reviewed."),
            ("BC − AC over +20 dB", "10 ears",
             "Not physiological. Chart review, then exclude."),
            ("AC − BC over 60 dB", "15 ears",
             "Likely mismatched masked and unmasked values."),
            ("Identical binaural vectors", "2 patients",
             "Patients 28 and 42. Symmetry, or a copy."),
            ("No records in 2023", "0 ears",
             "A full calendar year inside the window."),
            ("Likely batched sampling", "5 months at 22",
             "Consecutive is claimed, not what the file shows."),
            ("Unreadable dates", "6 rows",
             "Seo, Msr, Mar 25 and two blanks. Logged."),
        ]),
        ("FIXABLE", "mechanical, done on a copy", FIX, FIX_T, "→",
         ["These run in clean.py against a copy. The export itself is never edited, and every "
          "change is logged with its rule."], [
            ("Non-standard date strings", "58 rows",
             "54 case, 2 assumed year, 2 blank. All logged."),
            ("csoM capitalisation", "15 ears",
             "Canonicalised to csom. Token only."),
            ("120 dB HL as a ceiling code", "143 cells",
             "Across 54 ears. Flagged, no threshold altered."),
            ("3 kHz structurally missing", "200 ears",
             "Cannot be repaired. Declare it instead."),
        ]),
        ("REVIEW AND LIMIT", "a judgement call, or a sentence in the methods", REVIEW, REVIEW_T, "~", [], [
            ("BC − AC over +10 dB", "59 ears",
             "43 at 2 kHz, maximum +45. Flag and retain."),
            ("40 dB monotonicity jump", "18 ears",
             "Flagged for review, not corrected."),
            ("3 kHz loss from mid-2022", "200 ears",
             "3 kHz analyses cover 2020 to 2022 only."),
            ("other and not_documented", "137 and 92",
             "55.9% carry no named diagnosis."),
            ("2023 as a limitation", "0 ears",
             "It bears on representativeness either way."),
            ("Negative BC at −5 dB", "9 cells",
             "Inside the declared range. A normal value."),
        ]),
        ("BLOCKER", "settle before the primary analysis", PROB, "#F3DFE3", "!", [], [
            ("The index cannot classify", "20 ears",
             "4.9%. 16 shape, 4 severity. Worst ears."),
            ("Protocol and script disagree", "6 against 5",
             "25/40/60/80 answers another question."),
            ("390 or 410, not both", "one run",
             "Every figure in section 6 is on 390."),
        ]),
    ]

    gapx = 30
    colw = (W - 2 * PAD - gapx * 3) / 4
    TS, NS, CS = 8.6, 7.7, 9.4       # title, note, count

    def ch(name, note):
        ntl = len(Canvas(10).wrap(name, TS, colw - 36, True))
        nnl = len(Canvas(10).wrap(note, NS, colw - 36))
        return (16 + ntl * lh(TS, 1.20) + 8 + lh(CS, 1.12) + 6
                + nnl * lh(NS, 1.28) + 14)

    m = Canvas(10)
    subs = [c[1] for c in cols]
    head_h = 22 + max(len(m.wrap(sb, 7.8, colw - 22)) for sb in subs) * lh(7.8, 1.28) + 22
    body_h = max(sum(ch(n, t) + 8 for n, _, t in c[6]) for c in cols)

    c = Canvas(int(70 + head_h + body_h + 40 + 170))
    c.tracked(PAD, 4, "every defect, once, by what has to happen to it", 7.2, MUTED, True, 0.22)

    y0 = 62
    for ci, (title, sub, colour, tint, glyph, footnote, items) in enumerate(cols):
        x = PAD + ci * (colw + gapx)
        c.tracked(x, y0, title, 7.6, colour, True, 0.2)
        c.para(x, y0 + 26, sub, 7.8, colw - 10, MUTED, 1.28)
        y = y0 + head_h
        for name, count, note in items:
            lines = c.wrap(name, TS, colw - 36, True)
            h = ch(name, note)
            c.rect(x, y, colw, h, fill=tint)
            c.rect(x, y, 4, h, fill=colour)
            ty = y + 16
            for ln in lines:
                c.text_top(x + 18, ty, ln, TS, INK, True)
                ty += lh(TS, 1.20)
            ty += 8
            c.text_top(x + 18, ty, count, CS, colour, True)
            ty += lh(CS, 1.12) + 6
            c.para(x + 18, ty, note, NS, colw - 36, MUTED, 1.28)
            y += h + 8
        c.text_top(x, y + 2, f"{len(items)} findings", 8.0, MUTED)
        if footnote:
            c.para(x, y + 40, footnote[0], 8.0, colw - 20, MUTED, 1.40)

    fy = y0 + head_h + body_h + 34
    c.line(0, fy, W, fy, RULE, 2)
    c.text(PAD, fy + 34 + cap(28), "18", 28, INK, True)
    c.text_top(PAD + 190, fy + 28, "findings in the audit, and three of them block a submission.",
               11.2, INK, True)
    end = c.para(PAD, fy + 34 + cap(28) + 14,
                 "Query and fixable are different futures: a query may change a number, a fix "
                 "changes only its spelling. Nothing here was corrected silently, and no record "
                 "was dropped.", 9.0, W - 20, MUTED, 1.45)
    c._max_y = end + 22
    return c.save("p05_triage")


if __name__ == "__main__":
    for fn in (p01_summary, p02_pipeline, p03_schemes, p04_calendar, p05_triage):
        fn()
    if WARN:
        print("WARNINGS:")
        for w in WARN[:20]:
            print("  " + w)
