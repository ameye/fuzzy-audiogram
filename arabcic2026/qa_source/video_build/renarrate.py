"""Re-narrate only slides whose notes changed, then re-concat each deck."""
import asyncio, json, os, re, subprocess
import edge_tts
from pptx import Presentation

VOICE = "en-NG-AbeoNeural"
BASE = "/opt/data/acic_video"
DEL = "/home/hermes/.hermes/deliver"

FIX = {
    "surgeon in working in Tabuk": "surgeon working in Tabuk",
    "I will be be precise": "I will be precise",
    "maintain the  status quo": "maintain status quo",
}


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


notes = parse(f"{BASE}/edited/notes_v2.md")
for k in notes:
    for a, b in FIX.items():
        notes[k] = notes[k].replace(a, b)

DECKS = [
    ("fuzzy", "A Fuzzy Logic Framework", f"{BASE}/fuzzy"),
    ("saudi", "Hearing Loss Burden", f"{BASE}/saudi"),
]

changed_report = {}
for tag, prefix, d in DECKS:
    old = json.load(open(f"{d}/durations.json"))
    durs, changed = list(old), []
    items = sorted([k for k in notes if k[0].startswith(prefix)], key=lambda k: k[1])
    for deck, idx in items:
        text = notes[(deck, idx)]
        mp3 = f"{d}/say{idx:02d}.mp3"
        seg = f"{d}/seg{idx:02d}.mp4"
        prev = durs[idx - 1] if idx - 1 < len(durs) else 0
        # synthesise to a temp file, compare duration to detect change
        tmp = f"{d}/_probe{idx:02d}.mp3"
        asyncio.run(edge_tts.Communicate(text, VOICE, rate="+0%").save(tmp))
        dd = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", tmp], capture_output=True, text=True).stdout.strip())
        if True:  # full rebuild: compare nothing, regenerate everything
            os.replace(tmp, mp3)
            durs[idx - 1] = dd
            changed.append(idx)
        else:
            os.remove(tmp)
            durs[idx - 1] = prev
    # rebuild segments for changed slides only
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1")
    for idx in changed:
        dv = durs[idx - 1]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
                        "-i", f"{d}/slide{idx:02d}.png", "-i", f"{d}/say{idx:02d}.mp3",
                        "-t", f"{dv + 0.6:.2f}", "-af", "apad=pad_dur=0.6", "-vf", vf,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", f"{d}/seg{idx:02d}.mp4"],
                       check=True)
    json.dump(durs, open(f"{d}/durations.json", "w"))
    segs = sorted(f"{d}/{f}" for f in os.listdir(d) if f.startswith("seg") and f.endswith(".mp4"))
    lst = f"{d}/concat_abs.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(s)}'\n" for s in segs))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", f"{d}/presentation.mp4"], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=nw=1:nk=1", f"{d}/presentation.mp4"],
                               capture_output=True, text=True).stdout)
    changed_report[tag] = {"changed": changed, "duration": dur, "segs": len(segs)}
    print(f"{tag}: changed {changed} | {len(segs)} segs | {dur:.1f}s = {dur/60:.2f} min")

json.dump(changed_report, open(f"{BASE}/edited/rebuild_report.json", "w"), indent=1)
