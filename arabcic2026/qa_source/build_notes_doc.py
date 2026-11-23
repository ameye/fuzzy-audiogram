"""Build the speaker-notes rehearsal document from the extracted notes."""
import json

raw = json.load(open("/opt/data/speaker_notes_raw.json"))
WPM = 130

md = []
md.append("# ArabCIC 2026 — Speaker notes\n")
md.append("Distilled from the two presentation files on 23 November 2026. "
          "Every number in these notes matches the current decks.\n")
md.append("Timing assumes **130 words per minute**, which is a measured delivery pace "
          "for technical material rather than a conversational one.\n")

cur = None
for row in raw:
    if row[0] == "DECK":
        _, title, fn, slot, nslides = row
        if cur:
            w = cur["words"]
            mins = w / WPM
            md.append("")
            md.append(f"**Deck total: {w} words, {mins:.1f} minutes.** "
                      f"Slot is {cur['slot']} minutes, so "
                      + (f"**this overruns by {mins-cur['slot']:.1f} minutes — about "
                         f"{int((mins-cur['slot'])*WPM)} words to cut.**"
                         if mins > cur["slot"] else "it fits with room to spare.")
                      + "\n")
        cur = {"words": 0, "slot": slot}
        md.append(f"\n---\n\n## {title}\n")
        md.append(f"{nslides} slides, {slot}-minute slot.\n")
        md.append("\n| Slide | Words | Running time |\n|---|---|---|\n")
        # timing table placeholder filled below
        cur["table_start"] = len(md)
        cur["rows"] = []
        md.append("")
        continue

    _, idx, head, note, w = row
    cur["words"] += w
    cur["rows"].append(f"| {idx} | {w} | {w/WPM*60:.0f} s |")
    md.append(f"\n### Slide {idx} — {head}\n")
    md.append(note.replace("\n", " ") if note else "*No notes on this slide.*")
    md.append("")

# fill tables
for i, row in enumerate(raw):
    pass

# rebuild with tables inserted
md2 = []
deck_i = -1
for line in md:
    md2.append(line)

# simpler: re-emit with tables inline
md = []
cur = None
for row in raw:
    if row[0] == "DECK":
        if cur:
            mins = cur["words"] / WPM
            md.append(f"\n**Deck total: {cur['words']} words, {mins:.1f} minutes.** "
                      f"Slot {cur['slot']} min — "
                      + (f"**overruns by {mins-cur['slot']:.1f} min, about "
                         f"{int((mins-cur['slot'])*WPM)} words to cut.**"
                         if mins > cur["slot"] else "fits.")
                      + "\n")
            md.append("\n---\n")
        _, title, fn, slot, nslides = row
        cur = {"words": 0, "slot": slot, "rows": []}
        md.append(f"\n## {title}\n")
        md.append(f"{nslides} slides. Slot {slot} minutes.\n")
        md.append("\n<!--TABLE-->\n")
        continue
    _, idx, head, note, w = row
    cur["words"] += w
    cur["rows"].append(f"| {idx} | {w} | {w/WPM*60:.0f} s |")
    md.append(f"\n### Slide {idx} — {head}\n")
    md.append((note.replace("\n", " ") if note else "*No notes on this slide.*") + "\n")

mins = cur["words"] / WPM
md.append(f"\n**Deck total: {cur['words']} words, {mins:.1f} minutes.** "
          f"Slot {cur['slot']} min — "
          + (f"**overruns by {mins-cur['slot']:.1f} min, about "
             f"{int((mins-cur['slot'])*WPM)} words to cut.**" if mins > cur["slot"] else "fits.")
          + "\n")

text = "".join(md)

# insert the per-slide timing tables
parts = text.split("<!--TABLE-->")
if len(parts) == 3:
    rows_by_deck = [[r for r in raw if r[0] == "DECK"]]
    d0 = [r for r in raw if r[0] == "SLIDE"][:15]
    d1 = [r for r in raw if r[0] == "SLIDE"][15:]
    t0 = "| Slide | Words | Time |\n|---|---|---|\n" + "\n".join(
        f"| {r[1]} | {r[4]} | {r[4]/WPM*60:.0f} s |" for r in d0) + "\n"
    t1 = "| Slide | Words | Time |\n|---|---|---|\n" + "\n".join(
        f"| {r[1]} | {r[4]} | {r[4]/WPM*60:.0f} s |" for r in d1) + "\n"
    text = parts[0] + t0 + parts[1] + t1 + parts[2]

open("/opt/data/acic_qa/speaker_notes.md", "w").write(text)
print("written", len(text), "chars")
