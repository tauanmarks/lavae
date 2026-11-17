"""micro.py P W clip:a:b ... — splits a range into word-ish bursts (gap 0.12s) and transcribes each burst."""
import subprocess, sys, wave
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
P = Path(sys.argv[1]); W = Path(sys.argv[2])
for spec in sys.argv[3:]:
    n, a0, b0 = spec.split(":"); a0 = float(a0); b0 = float(b0)
    w = wave.open(str(P / f"IMG_{n}.wav")); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    seg = x[int(a0 * sr):int(b0 * sr)]
    hop = int(sr * 0.01)
    db = np.array([20 * np.log10(np.sqrt(np.mean(seg[i:i + hop] ** 2)) + 1e-9) for i in range(0, len(seg) - hop, hop)])
    act = db > -37
    bursts = []; i = 0
    while i < len(act):
        if act[i]:
            j = i
            while j < len(act) and act[j]: j += 1
            if bursts and (i - bursts[-1][1]) * 0.01 < 0.12: bursts[-1][1] = j
            else: bursts.append([i, j])
            i = j
        else: i += 1
    print(f"######## {n} {a0}–{b0}")
    for a, b in bursts:
        if (b - a) * 0.01 < 0.08: continue
        ta, tb = a0 + a * 0.01, a0 + b * 0.01
        tmp = P / "micro.wav"
        s2 = x[int((ta - 0.05) * sr):int((tb + 0.05) * sr)]
        with wave.open(str(tmp), "wb") as o:
            o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes((s2 * 32767).astype(np.int16).tobytes())
        r = subprocess.run([str(W / "whisper-cli.exe"), "-m", str(W / "models" / "ggml-large-v3-turbo-q5_0.bin"), "-f", str(tmp), "-l", "pt", "-np", "-nt", "-t", "8"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"  {ta:7.2f}–{tb:7.2f}  {' '.join(r.stdout.split())}")
