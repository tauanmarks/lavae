"""Splits each speech clip into phrases by energy (adaptive threshold) and transcribes each phrase."""
import json, subprocess, sys, wave, os
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
P = Path(sys.argv[1]); W = Path(sys.argv[2]); MODEL = sys.argv[3]
clips = sys.argv[4].split(",")
out = {}
for n in clips:
    w = wave.open(str(P / f"IMG_{n}.wav")); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    hop = int(sr * 0.02)
    db = np.array([20 * np.log10(np.sqrt(np.mean(x[i:i + hop] ** 2)) + 1e-9) for i in range(0, len(x) - hop, hop)])
    speech_lvl = np.percentile(db, 90)
    thr = speech_lvl - float(os.environ.get("OFF", "18"))
    act = db > thr
    # close gaps < 0.35s, drop blips < 0.25s
    segs = []; i = 0; N = len(act)
    while i < N:
        if act[i]:
            j = i
            while j < N and act[j]: j += 1
            segs.append([i, j]); i = j
        else: i += 1
    merged = []
    for a, b in segs:
        if merged and (a - merged[-1][1]) * 0.02 < float(os.environ.get("GAP", "0.35")): merged[-1][1] = b
        else: merged.append([a, b])
    merged = [(a * 0.02, b * 0.02) for a, b in merged if (b - a) * 0.02 >= 0.25]
    print(f"######## {n}  (fala ~{speech_lvl:.0f} dB, limiar {thr:.0f} dB)")
    res = []
    for a, b in merged:
        a2, b2 = max(0, a - 0.1), b + 0.1
        tmp = P / "chunk.wav"
        seg = x[int(a2 * sr):int(b2 * sr)]
        with wave.open(str(tmp), "wb") as o:
            o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes((seg * 32767).astype(np.int16).tobytes())
        r = subprocess.run([str(W / "whisper-cli.exe"), "-m", str(W / "models" / MODEL), "-f", str(tmp), "-l", "pt", "-np", "-nt", "-t", "8"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        txt = " ".join(r.stdout.split())
        res.append({"a": round(a, 2), "b": round(b, 2), "txt": txt})
        print(f"  {a:7.2f}–{b:7.2f} ({b - a:4.1f}s)  {txt}")
    out[n] = res
json.dump(out, open(P / os.environ.get("OUTJ", "frases.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
