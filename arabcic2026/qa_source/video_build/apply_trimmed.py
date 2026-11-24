"""Fix the GBD year, apply trimmed notes to both decks, leave the references slide alone."""
import re
from pptx import Presentation

DEL = "/home/hermes/.hermes/deliver"
FUZZY = f"{DEL}/ACIC2026_Fuzzy_SNHL_Classification.pptx"
SAUDI = f"{DEL}/ACIC2026_HearingLoss_GBD2023_Saudi.pptx"
TRIM = f"{DEL}/ACIC2026_Speaker_Notes_trimmed.md"


def parse(p):
    txt = open(p, encoding="utf-8").read()
    d, deck, i = {}, None, None
    for ln in txt.split("\n"):
        if ln.startswith("## "):
            deck, i = ln[3:].strip(), None
            continue
        m = re.match(r"### Slide (\d+)", ln)
        if m:
            i = int(m.group(1))
            d[(deck, i)] = []
            continue
        if i is None or ln.startswith(("|", "**Deck", "---", "# ")):
            continue
        if ln.strip():
            d[(deck, i)].append(ln.strip())
    return {k: " ".join(v) for k, v in d.items()}


notes = parse(TRIM)
print(f"parsed {len(notes)} note blocks")
for k in sorted(notes)[:2]:
    print(f"  {k[0][:30]} s{k[1]}: {len(notes[k].split())}w")

# 1. GBD year fix on the Saudi deck
prs = Presentation(SAUDI)
fixes = 0
for idx in (4, 14):
    for sh in prs.slides[idx - 1].shapes:
        if not sh.has_text_frame:
            continue
        for para in sh.text_frame.paragraphs:
            for r in para.runs:
                if "IHME 2024" in r.text:
                    r.text = r.text.replace("IHME 2024", "IHME 2025")
                    fixes += 1
prs.save(SAUDI)
print(f"\nGBD year fixed in {fixes} run(s) on Saudi slides 4 and 14")

# 2. apply trimmed notes
applied = {}
for path, prefix in ((FUZZY, "A Fuzzy"), (SAUDI, "Hearing Loss Burden")):
    prs = Presentation(path)
    n = 0
    total = 0
    for (deck, idx), text in sorted(notes.items(), key=lambda x: x[0][1]):
        if not deck.startswith(prefix):
            continue
        if idx > len(prs.slides):
            print(f"  !! {prefix} slide {idx} does not exist")
            continue
        s = prs.slides[idx - 1]
        s.notes_slide.notes_text_frame.text = text
        n += 1
        total += len(text.split())
    prs.save(path)
    applied[path.split("/")[-1]] = (n, total, len(prs.slides))
    print(f"{path.split('/')[-1]}: {n} notes applied over {len(prs.slides)} slides, {total} words, {total/130:.2f} min")

# 3. verify
print("\n=== verify ===")
for path in (FUZZY, SAUDI):
    prs = Presentation(path)
    last = prs.slides[-1]
    head = " ".join(last.shapes[0].text_frame.text.split())[:40] if last.shapes else ""
    s1 = prs.slides[0].notes_slide.notes_text_frame.text
    s4 = " | ".join(r.text for sh in prs.slides[3].shapes if sh.has_text_frame
                    for p in sh.text_frame.paragraphs for r in p.runs if "IHME" in r.text)
    print(f"{path.split('/')[-1]}: {len(prs.slides)} slides | last slide: {head!r}")
    print(f"   slide1 note starts: {s1[:60]!r}")
    print(f"   slide4 IHME text: {s4[:90]!r}")
    print(f"   refs-slide notes empty: {not last.notes_slide.notes_text_frame.text.strip()}")
