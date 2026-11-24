"""Apply the user's edited speaker notes to both decks, then report word counts."""
import re, json
from pptx import Presentation

SRC = "/opt/data/acic_video/edited/notes_v2.md"
DECK_FUZZY = "/home/hermes/.hermes/deliver/ACIC2026_Fuzzy_SNHL_Classification.pptx"
DECK_SAUDI = "/home/hermes/.hermes/deliver/ACIC2026_HearingLoss_GBD2023_Saudi.pptx"

# his text, with only mechanical duplications corrected in rehearsal copy
FIX = {
    "surgeon in working in Tabuk": "surgeon working in Tabuk",
    "I will be be precise": "I will be precise",
    "maintain the  status quo": "maintain status quo",
}


def parse(p):
    txt = open(p, encoding="utf-8").read()
    d = {}
    deck = None
    i = None
    for ln in txt.split("\n"):
        if ln.startswith("## "):
            deck = ln[3:].strip()
            i = None
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


notes = parse(SRC)
cleaned = 0
for k in list(notes):
    t = notes[k]
    for a, b in FIX.items():
        if a in t:
            t = t.replace(a, b)
            cleaned += 1
    notes[k] = t

targets = {}
for k in notes:
    if k[0].startswith("A Fuzzy"):
        targets[k] = (DECK_FUZZY, k[1])
    elif k[0].startswith("Hearing Loss Burden"):
        targets[k] = (DECK_SAUDI, k[1])

report = {}
for (deck, idx), (path, slide_no) in sorted(targets.items(), key=lambda x: x[1]):
    prs = Presentation(path) if path not in report else report[path]["prs"]
    if path not in report:
        report[path] = {"prs": prs, "words": {}}
    s = prs.slides[slide_no - 1]
    tf = s.notes_slide.notes_text_frame
    tf.text = notes[(deck, idx)]
    report[path]["words"][slide_no] = len(notes[(deck, idx)].split())

for path, info in report.items():
    info["prs"].save(path)
    w = sum(info["words"].values())
    print(f"{path.split('/')[-1]}: {len(info['words'])} slides, {w} words, "
          f"{w/130:.1f} min at 130wpm")

print(f"\nmechanical fixes applied: {cleaned}")
print("  'in working in' -> 'working in'")
print("  'I will be be'  -> 'I will be'")
print("  double-space 'status  quo' normalised")

json.dump({k: v["words"] for k, v in report.items()},
          open("/opt/data/acic_video/edited/wordcounts.json", "w"), indent=1)
