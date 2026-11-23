# -*- coding: utf-8 -*-
"""Build the ACIC 2026 Q&A preparation sheet (A4, one page per deck).

Writes ACIC2026_QandA_Prep.html next to this file. The page carries a
self-fitting routine: it measures every entry against the bottom band and
picks the largest body size that fits without collision. Print it with
Page.printToPDF (preferCSSPageSize, zero margins) and verify the page count.
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from qa_content import DECK1, DECK2  # noqa: E402

OUT = Path(__file__).parent / "ACIC2026_QandA_Prep.html"

CHIP = {"H": ("h", "Hard"), "M": ("m", "Medium"), "L": ("l", "Light")}
BARS = {"H": 3, "M": 2, "L": 1}


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def entry(i: int, q: dict) -> str:
    cls, label = CHIP[q["lvl"]]
    bars = "".join("<b></b>" for _ in range(3))
    on = BARS[q["lvl"]]
    bars = "".join(
        f'<b class="on"></b>' if k < on else "<b></b>" for k in range(3)
    )
    return f"""<div class="e">
  <p class="qh"><span class="n">{i}</span><span class="chip {cls}">{label}<i class="bars">{bars}</i></span><span class="q">{esc(q['q'])}</span></p>
  <p class="a">{esc(q['a'])}</p>
  <p class="d"><span class="dl">Don&rsquo;t say</span> {esc(q['d'])}</p>
</div>"""


def split_cols(qs):
    """Split entries into two columns of roughly equal measured weight."""
    weights = [len(q["q"]) * 1.35 + len(q["a"]) + len(q["d"]) * 0.9 + 120 for q in qs]
    total = sum(weights)
    run, cut = 0.0, len(qs) // 2
    for i, w in enumerate(weights):
        run += w
        if run >= total / 2:
            cut = i + 1
            break
    cut = max(4, min(cut, len(qs) - 4))
    return qs[:cut], qs[cut:]


def page(d: dict, first: bool) -> str:
    left, right = split_cols(d["qs"])
    i0 = 0
    left_html = []
    for q in left:
        i0 += 1
        left_html.append(entry(i0, q))
    right_html = []
    for q in right:
        i0 += 1
        right_html.append(entry(i0, q))
    asks = "".join(f"<li>{esc(a)}</li>" for a in d["ask"])
    cls = "page" if first else "page second"
    return f"""<section class="{cls}">
  <header class="hd">
    <div class="kick">{esc(d['kicker'])}</div>
    <div class="trow">
      <div class="tcol">
        <h1>{esc(d['title'])}</h1>
        <div class="sub">{esc(d['sub'])}</div>
      </div>
      <div class="badge"><span class="bn">{d['num']}</span><span class="bl">deck</span></div>
    </div>
    <div class="hmeta"><span>{esc(d['meta'])}</span><span class="key"><em>Hard</em><i class="chip h"><i class="bars"><b class="on"></b><b class="on"></b><b class="on"></b></i></i><em>Medium</em><i class="chip m"><i class="bars"><b class="on"></b><b class="on"></b><b></b></i></i><em>Light</em><i class="chip l"><i class="bars"><b class="on"></b><b></b><b></b></i></i></span></div>
  </header>
  <div class="cols">{''.join(left_html)}{''.join(right_html)}</div>
  <div class="band">
    <div class="ifdk">
      <h3>If you do not know</h3>
      <p class="idk">&ldquo;{esc(d['ifdk'])}&rdquo;</p>
      <p class="idkn">Say it in that shape, then stop. Do not fill the silence with a number.</p>
    </div>
    <div class="ask">
      <h3>Ask the room</h3>
      <ol>{asks}</ol>
    </div>
  </div>
  <footer class="ft"><span>{esc(d['source'])}</span><span>{esc(d['footer'])}  ·  page {'1' if first else '2'} of 2</span></footer>
</section>"""


CSS = """
:root { --fs: 7.8pt; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #F5F1E8; }
body { font-family: "Source Sans 3", sans-serif; color: #1B2A3A;
       -webkit-font-smoothing: antialiased; }
@page { size: A4; margin: 0; }
.page { --pfs: 7.10pt; font-size: var(--pfs); width: 210mm; height: 297mm; padding: 7.5mm 9mm 5.5mm;
        display: flex; flex-direction: column; position: relative;
        background: #F5F1E8; overflow: hidden; page-break-after: always; }
.page.second { page-break-after: auto; }
.page::before { content: ""; position: absolute; left: 0; right: 0; top: 0;
        height: 3.2mm; background: #0B2545; }
.page::after { content: ""; position: absolute; left: 0; right: 0; top: 3.2mm;
        height: 0.45mm; background: #E8B54A; }

/* header */
.hd { flex: 0 0 auto; padding-top: 1.8mm; }
.kick { font-size: 6.5pt; font-weight: 600; letter-spacing: .145em;
        text-transform: uppercase; color: #1D7874; }
.trow { display: flex; align-items: flex-end; justify-content: space-between;
        gap: 6mm; margin-top: 2.1mm; }
h1 { font-family: Gelasio, serif; font-weight: 600; font-size: 15.6pt;
     line-height: 1.08; color: #0B2545; margin: 0; letter-spacing: -.005em; }
.sub { font-size: 8.3pt; color: #4A5A6A; margin-top: 1.2mm; font-style: italic;
       font-family: Gelasio, serif; }
.badge { text-align: right; line-height: 1; padding-bottom: .6mm; }
.bn { font-family: Gelasio, serif; font-size: 22pt; color: #C9A227; font-weight: 600;
      display: block; letter-spacing: -.02em; }
.bl { font-size: 5.8pt; letter-spacing: .22em; text-transform: uppercase;
      color: #8A94A6; }
.hmeta { display: flex; justify-content: space-between; align-items: center;
         margin-top: 2.4mm; padding-top: 1.5mm; border-top: 1.4pt solid #0B2545;
         font-size: 6.7pt; color: #5A6B7B; letter-spacing: .02em; }
.key { display: flex; align-items: center; gap: 1.2mm; }
.key em { font-style: normal; font-size: 6pt; letter-spacing: .1em;
          text-transform: uppercase; color: #5A6B7B; margin-right: .6mm; }

/* difficulty chips */
.chip { display: inline-flex; align-items: center; gap: .7mm; font-size: .78em;
        font-weight: 700; letter-spacing: .075em; text-transform: uppercase;
        padding: .45mm 1mm .45mm 1.1mm; border-radius: .5mm; line-height: 1;
        vertical-align: .18em; white-space: nowrap; }
.chip.h { background: #0B2545; color: #FFFFFF; }
.chip.m { background: #E8B54A; color: #0B2545; }
.chip.l { background: #D9D2C2; color: #3A4654; }
.chip i.bars { display: inline-flex; gap: .3mm; }
.chip i.bars b { width: .78mm; height: .78mm; background: rgba(255,255,255,.32);
                 display: block; }
.chip.m i.bars b { background: rgba(11,37,69,.22); }
.chip.l i.bars b { background: rgba(11,37,69,.2); }
.chip i.bars b.on { background: #FFFFFF; }
.chip.m i.bars b.on { background: #0B2545; }
.chip.l i.bars b.on { background: #3A4654; }
.key .chip { font-size: 0 !important; padding: .5mm .9mm; }
.key .chip i.bars b { width: .8mm; height: .8mm; }

/* body */
.cols { flex: 1 1 auto; min-height: 0; margin-top: 3mm; column-count: 2;
        column-gap: 9mm; column-rule: .4pt solid #D8D2C4; font-size: 1em;
        line-height: 1.34; }
.e { break-inside: avoid; page-break-inside: avoid; margin-bottom: 2.2mm;
     padding-bottom: 2.0mm; border-bottom: .35pt solid #E2DACB; }
.e:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.qh { margin: 0; }
.n { font-family: Gelasio, serif; font-size: 1.02em; font-weight: 600;
     color: #1D7874; margin-right: 1mm; }
.q { font-weight: 650; color: #0B2545; }
.a { margin: .85mm 0 0; text-align: left; hyphens: auto; }
.d { margin: .75mm 0 0; font-size: .905em; font-style: italic; color: #6A5A44;
     border-left: 1.1pt solid #E8B54A; padding-left: 1.5mm; hyphens: auto; }
.d .dl { font-style: normal; font-weight: 700; font-size: .86em; letter-spacing: .09em;
         text-transform: uppercase; color: #A8762B; margin-right: .8mm; }

/* bottom band */
.band { flex: 0 0 auto; display: flex; gap: 6mm; margin-top: 2.2mm;
        padding-top: 2.0mm; border-top: 1.4pt solid #0B2545; }
.ifdk { flex: 1.05 1 0; }
.ask { flex: 1 1 0; padding-left: 6mm; border-left: .4pt solid #D8D2C4; }
.band h3 { font-size: 6.4pt; letter-spacing: .16em; text-transform: uppercase;
           color: #1D7874; margin: 0 0 1.4mm; font-weight: 700; }
.idk { font-family: Gelasio, serif; font-size: 8.5pt; line-height: 1.36;
       color: #0B2545; margin: 0; font-style: italic; }
.idkn { font-size: 6.5pt; color: #7A6A55; margin: 1.3mm 0 0; }
.ask ol { margin: 0; padding-left: 3.6mm; }
.ask li { font-size: 7.2pt; line-height: 1.34; margin-bottom: .9mm; }
.ask li::marker { color: #C9A227; font-weight: 700; }

.ft { flex: 0 0 auto; display: flex; justify-content: space-between; gap: 6mm;
      margin-top: 2.4mm; padding-top: 1.2mm; border-top: .4pt solid #D8D2C4;
      font-size: 5.9pt; color: #8A94A6; letter-spacing: .02em; }
"""

FIT_JS = """
(() => {
  const pages = [...document.querySelectorAll('.page')];
  const out = pages.map((p) => {
    const cols = p.querySelector('.cols');
    let pick = null;
    for (let s = 8.60; s >= 6.20; s -= 0.05) {
      p.style.setProperty('--pfs', s.toFixed(2) + 'pt');
      document.body.getBoundingClientRect();
      if (cols.scrollWidth <= cols.clientWidth + 1 &&
          cols.scrollHeight <= cols.clientHeight + 1) { pick = s; break; }
    }
    if (pick === null) pick = 6.20;
    p.style.setProperty('--pfs', pick.toFixed(2) + 'pt');
    document.body.getBoundingClientRect();
    const band = p.querySelector('.band').getBoundingClientRect();
    const es = [...p.querySelectorAll('.e')];
    const bottoms = es.map(e => e.getBoundingClientRect().bottom);
    return {fs: pick.toFixed(2),
            usedW: Math.round(cols.scrollWidth), clientW: Math.round(cols.clientWidth),
            gap: Math.round(band.top - Math.max(...bottoms))};
  });
  return JSON.stringify(out);
})()
"""


def build(fs="7.80") -> Path:
    doc = f"""<!DOCTYPE html>
<html lang="en-GB"><head><meta charset="utf-8">
<title>ACIC 2026 Q&amp;A preparation</title>
<style>{CSS.replace('--fs: 7.8pt', f'--fs: {fs}pt')}</style>
</head><body>
{page(DECK1, True)}
{page(DECK2, False)}
<script>window.__FIT__ = {FIT_JS};</script>
</body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    words = sum(len((q["q"] + " " + q["a"] + " " + q["d"]).split())
                for d in (DECK1, DECK2) for q in d["qs"])
    print(f"wrote {OUT}  ({len(doc)} bytes, {words} words of Q&A)")
    return OUT


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "7.80")
