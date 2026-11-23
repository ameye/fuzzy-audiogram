"""Distil the speaker notes from both ACIC decks into a rehearsal document."""
from pptx import Presentation
import json, os

DECKS = [
    ("ACIC2026_Fuzzy_SNHL_Classification.pptx",
     "A Fuzzy Logic Framework for SNHL Classification", 10),
    ("ACIC2026_HearingLoss_GBD2023_Saudi.pptx",
     "Hearing Loss Burden in Saudi Arabia: Machine-Learning Analysis of GBD 2023", 10),
]
DEL = "/home/hermes/.hermes/deliver"
WPM = 130

out = []
total_words = {}

for fn, title, slot in DECKS:
    p = Presentation(os.path.join(DEL, fn))
    out.append(("DECK", title, fn, slot, len(p.slides)))
    words = 0
    for i, s in enumerate(p.slides, 1):
        n = s.notes_slide.notes_text_frame.text.strip() if s.has_notes_slide else ""
        # slide headline = first substantial text shape
        head = ""
        for sh in s.shapes:
            if sh.has_text_frame:
                t = " ".join(sh.text_frame.text.split())
                if 12 < len(t) < 90 and not t.startswith(("ArabCIC", "4TH ARAB")):
                    head = t
                    break
        w = len(n.split())
        words += w
        out.append(("SLIDE", i, head, n, w))
    total_words[fn] = (words, slot)

json.dump(out, open("/opt/data/speaker_notes_raw.json", "w"), indent=1)
for fn, (w, slot) in total_words.items():
    mins = w / WPM
    print(f"{fn}: {w} words, {mins:.1f} min at {WPM} wpm, slot {slot} min "
          f"-> {'OVER by %.1f min (%d words to cut)' % (mins-slot, int((mins-slot)*WPM)) if mins>slot else 'fits'}")
