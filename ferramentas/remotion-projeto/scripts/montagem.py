"""montagem.py PLANO.json PUBLIC_DIR OUT_DIR
Builds the final shot list from a multi-clip plan, trimming internal pauses > MIN_SIL in speech ranges.
PLANO.json: [{"clip": "IMG_9867", "a": 1.2, "b": 5.0, "speed": 1, "fala": true}, ...]
Writes OUT_DIR/planos.json (shots with src times + output times) and OUT_DIR/preview.wav (speech concatenated, b-roll as silence)."""
import json, re, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
plano = json.load(open(sys.argv[1], encoding="utf-8")); PUB = Path(sys.argv[2]); OUT = Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
import os
NOISE, MIN_SIL, PAD = os.environ.get("NOISE", "-33dB"), 0.3, 0.07

def silences(src, a, b):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(a), "-to", str(b), "-i", src, "-af", f"silencedetect=noise={NOISE}:d={MIN_SIL}", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    st = [float(x) + a for x in re.findall(r"silence_start: ([\d.]+)", r)]
    en = [float(x) + a for x in re.findall(r"silence_end: ([\d.]+)", r)]
    return list(zip(st, en + [b] * (len(st) - len(en))))

shots, t = [], 0.0
for item in plano:
    # "arquivo": a pre-rendered file in PUB (e.g. a speed-up) used instead of the clip; a/b are times in that file
    src = str(PUB / (item.get("arquivo") or f"{item['clip']}.mp4")); a, b = item["a"], item["b"]; sp = item.get("speed", 1)
    pieces = [(a, b)]
    if item.get("fala") and item.get("aparar", True):
        pieces, cur = [], a
        for s, e in silences(src, a, b):
            s2, e2 = s + PAD, e - PAD
            if s2 - cur > 0.1: pieces.append((cur, s2))
            cur = max(cur, e2)
        if b - cur > 0.1: pieces.append((cur, b))
        # no piece shorter than MIN_PIECE: re-join it with its neighbour (keeps that pause)
        MIN_PIECE = 0.6
        changed = True
        while changed and len(pieces) > 1:
            changed = False
            for i, (pa, pb) in enumerate(pieces):
                if pb - pa < MIN_PIECE:
                    j = i + 1 if i + 1 < len(pieces) else i - 1
                    lo, hi = sorted([i, j])
                    pieces[lo:hi + 1] = [(pieces[lo][0], pieces[hi][1])]
                    changed = True
                    break
    for pa, pb in pieces:
        d = (pb - pa) / sp
        shots.append({"clip": item["clip"], "a": round(pa, 3), "b": round(pb, 3), "speed": sp, "fala": bool(item.get("fala")), "t": round(t, 3), "d": round(d, 3), "tag": item.get("tag", ""), "arquivo": item.get("arquivo", "")})
        t += d
print(f"{len(shots)} planos, {t:.2f}s")
for s in shots:
    print(f"  {s['t']:6.2f}  {s['clip']} {s['a']:7.2f}–{s['b']:7.2f} x{s['speed']} {'fala' if s['fala'] else ''} {s['tag']}")
json.dump(shots, open(OUT / "planos.json", "w", encoding="utf-8"), indent=1)
# preview audio (speech as is, b-roll as silence)
inputs, flt = [], ""
for i, s in enumerate(shots):
    inputs += ["-i", str(PUB / f"{s['clip']}.mp4")]
    if s["fala"]:
        flt += f"[{i}:a]atrim={s['a']}:{s['b']},asetpts=PTS-STARTPTS,aresample=16000,pan=mono|c0=c0[a{i}];"
    else:
        flt += f"anullsrc=r=16000:cl=mono,atrim=0:{s['d']}[a{i}];"
flt += "".join(f"[a{i}]" for i in range(len(shots))) + f"concat=n={len(shots)}:v=0:a=1[o]"
subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", flt, "-map", "[o]", "-c:a", "pcm_s16le", str(OUT / "preview.wav")], check=True)
