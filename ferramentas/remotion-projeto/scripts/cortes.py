"""Builds keep-segments from silences + manual removals, writes cuts.json and a preview wav."""
import json, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

SRC = sys.argv[1]      # cleaned source video
OUT = sys.argv[2]      # output dir
REMOVE = json.loads(sys.argv[3])  # [[a,b],...] source seconds to drop
END = float(sys.argv[4])
PAD = 0.07             # keep this much of each silence on both sides
MIN_SIL = 0.28

r = subprocess.run(["ffmpeg", "-hide_banner", "-i", SRC, "-af", f"silencedetect=noise=-34dB:d={MIN_SIL}", "-f", "null", "-"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
drops = [(a + PAD, b - PAD) for a, b in zip(st, en)] + [tuple(x) for x in REMOVE] + [(END, 1e9)]
drops.sort()
merged = []
for a, b in drops:
    if merged and a <= merged[-1][1]:
        merged[-1] = (merged[-1][0], max(merged[-1][1], b))
    else:
        merged.append((a, b))
keep, t = [], 0.0
for a, b in merged:
    if a - t > 0.12:
        keep.append([round(t, 3), round(a, 3)])
    t = max(t, b)
total = sum(b - a for a, b in keep)
print(f"{len(keep)} segmentos, {total:.2f}s")
for a, b in keep:
    print(f"  {a:6.2f} – {b:6.2f}  ({b - a:.2f}s)")
json.dump(keep, open(f"{OUT}/cuts.json", "w"), indent=0)
# preview audio
flt = "".join(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}];" for i, (a, b) in enumerate(keep))
flt += "".join(f"[a{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=0:a=1,aresample=16000,pan=mono|c0=c0[o]"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", SRC, "-filter_complex", flt, "-map", "[o]", "-c:a", "pcm_s16le", f"{OUT}/preview.wav"], check=True)
