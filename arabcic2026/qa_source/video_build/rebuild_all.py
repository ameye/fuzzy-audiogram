"""Full rebuild: render every slide, narrate the trimmed notes, compose."""
import asyncio, json, os, subprocess
import edge_tts, pymupdf
from pptx import Presentation

VOICE = "en-NG-AbeoNeural"
BASE = "/opt/data/acic_video"
DEL = "/home/hermes/.hermes/deliver"

DECKS = [
    ("fuzzy", "ACIC2026_Fuzzy_SNHL_Classification",
     "A Fuzzy Logic Framework"),
    ("saudi", "ACIC2026_HearingLoss_GBD2023_Saudi",
     "Hearing Loss Burden"),
]
VF = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
      "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1")

for tag, stem, prefix in DECKS:
    d = f"{BASE}/{tag}"
    pdf = f"{d}/{stem}.pdf"
    pptx = f"{DEL}/{stem}.pptx"

    # render all slides
    doc = pymupdf.open(pdf)
    for i, page in enumerate(doc, 1):
        m = pymupdf.Matrix(1920 / page.rect.width, 1920 / page.rect.width)
        page.get_pixmap(matrix=m).save(f"{d}/slide{i:02d}.png")
    npages = doc.page_count

    # notes, narration slides only (references slide has no notes)
    prs = Presentation(pptx)
    notes = [s.notes_slide.notes_text_frame.text.strip() if s.has_notes_slide else ""
             for s in prs.slides]
    narrate = [(i + 1, t) for i, t in enumerate(notes) if t.strip()]
    print(f"{tag}: {npages} slides rendered, {len(narrate)} narrated, "
          f"{len(notes) - len(narrate)} silent")

    # clean old segments
    for f in os.listdir(d):
        if f.startswith("seg") and f.endswith(".mp4"):
            os.remove(f"{d}/{f}")

    segs = []
    total = 0.0
    for idx, text in narrate:
        mp3 = f"{d}/say{idx:02d}.mp3"
        asyncio.run(edge_tts.Communicate(text, VOICE, rate="+0%").save(mp3))
        dd = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", mp3], capture_output=True, text=True).stdout.strip())
        total += dd
        seg = f"{d}/seg{idx:02d}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
                        "-i", f"{d}/slide{idx:02d}.png", "-i", mp3,
                        "-t", f"{dd + 0.6:.2f}", "-af", "apad=pad_dur=0.6", "-vf", VF,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", seg], check=True)
        segs.append(seg)
        print(f"   s{idx:02d} {len(text.split()):3d}w {dd:6.2f}s")

    lst = f"{d}/concat_abs.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(s)}'\n" for s in sorted(segs)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", f"{d}/presentation.mp4"], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of", "default=nw=1:nk=1",
                                f"{d}/presentation.mp4"], capture_output=True,
                               text=True).stdout)
    size = os.path.getsize(f"{d}/presentation.mp4") / 1e6
    print(f"{tag}: speech {total:.1f}s, video {dur:.1f}s = {dur/60:.2f} min, {size:.1f} MB\n")
    json.dump({"duration": dur, "size_mb": size, "slides": npages,
               "narrated": len(narrate)},
              open(f"{d}/final.json", "w"), indent=1)
