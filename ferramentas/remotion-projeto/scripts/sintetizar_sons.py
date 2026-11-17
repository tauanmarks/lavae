"""Synthesizes brand SFX (chime, pop, whoosh, click, sparkle) and a soft lo-fi bed (100 BPM)."""
import sys, wave
from pathlib import Path
import numpy as np

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
SR = 48000
rng = np.random.default_rng(7)

def save(name, x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    peak = np.max(np.abs(x)) or 1
    x = x / peak * 0.89
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())

def t(d): return np.arange(int(SR * d)) / SR

def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR); y = np.zeros_like(x); s = 0.0
    for i, v in enumerate(x):
        s = (1 - a) * v + a * s; y[i] = s
    return y

# chime: bell partials, quick arpeggio
def bell(f, d=1.4):
    tt = t(d)
    parts = [(1, 1.0), (2.76, 0.35), (5.4, 0.18), (8.93, 0.08)]
    return sum(a * np.sin(2 * np.pi * f * m * tt) * np.exp(-tt * (3 + m)) for m, a in parts)
ch = np.zeros(int(SR * 1.8))
for i, f in enumerate([1318.5, 1760.0, 2093.0, 2637.0]):
    s = int(SR * 0.055 * i); b = bell(f) * (0.9 - 0.12 * i); ch[s:s + len(b)] += b[: len(ch) - s]
save("chime.wav", ch)

# pop: pitched blip with fast down-sweep
tt = t(0.12); f = 900 * np.exp(-tt * 28) + 260
pop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 38)
save("pop.wav", pop)

# click: tiny filtered transient
tt = t(0.035); clk = (rng.standard_normal(len(tt)) * np.exp(-tt * 300) + np.sin(2 * np.pi * 3200 * tt) * np.exp(-tt * 200))
save("click.wav", np.concatenate([clk, np.zeros(1000)]))

# whoosh: noise with moving bandpass-ish (two lowpasses) and swell
d = 0.55; tt = t(d); n = rng.standard_normal(len(tt))
env = np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 2
hi = n - lowpass(n, 400); band = lowpass(hi, 3500)
L = band * env; R = np.roll(band, 200) * env
save("whoosh.wav", np.stack([L * np.linspace(1.2, .6, len(tt)), R * np.linspace(.6, 1.2, len(tt))], 1))

# sparkle: random high tinkles
sp = np.zeros(int(SR * 1.2))
for k in range(14):
    s = int(rng.uniform(0, 0.7) * SR); f0 = rng.uniform(2600, 5200); b = np.sin(2 * np.pi * f0 * t(0.35)) * np.exp(-t(0.35) * 14) * rng.uniform(.3, 1)
    sp[s:s + len(b)] += b
save("sparkle.wav", sp)

# ---- lo-fi bed, 100 BPM, 4 chords x 2 bars, looped to length ----
BPM = 100; beat = 60 / BPM; bar = beat * 4
length = float(sys.argv[2]) if len(sys.argv) > 2 else 44
N = int(SR * length); L = np.zeros(N); R = np.zeros(N)
def midi(m): return 440 * 2 ** ((m - 69) / 12)
chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]  # Fmaj7 Em7 Dm7 Cmaj7
def epiano(f, d):
    tt = t(d)
    env = (1 - np.exp(-tt * 60)) * np.exp(-tt * 1.3)
    tone = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 4) + 0.08 * np.sin(2 * np.pi * 3 * f * tt) * np.exp(-tt * 6)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * tt)
    return tone * env * trem
pos = 0.0; ci = 0
while pos < length:
    for rep in range(2):
        for hit in (0, 2.5):  # comp on beat 1 and the "and" of 3
            st = pos + (rep * bar) + hit * beat
            if st >= length: break
            for j, m in enumerate(chords[ci % 4]):
                x = epiano(midi(m), bar * 0.95) * 0.16
                s = int((st + j * 0.012) * SR); e = min(N, s + len(x))
                pan = 0.35 + 0.1 * j
                L[s:e] += x[: e - s] * (1 - pan); R[s:e] += x[: e - s] * pan
        # bass
        bt = pos + rep * bar; s = int(bt * SR)
        bx = np.sin(2 * np.pi * midi(chords[ci % 4][0] - 12) * t(bar * 0.9)) * np.exp(-t(bar * 0.9) * 1.6) * 0.32
        e = min(N, s + len(bx))
        if s < N: L[s:e] += bx[: e - s]; R[s:e] += bx[: e - s]
    pos += 2 * bar; ci += 1
# drums
k = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-t(0.3) * 30)) / SR) * np.exp(-t(0.3) * 12) * 0.6
sn = lowpass(rng.standard_normal(int(SR * 0.2)), 2500) * np.exp(-t(0.2) * 22) * 0.35
hh = (rng.standard_normal(int(SR * 0.05)) - lowpass(rng.standard_normal(int(SR * 0.05)), 5000)) * np.exp(-t(0.05) * 90) * 0.12
nb = int(length / beat) + 1
for b in range(nb):
    st = b * beat
    def add(x, at, g=1.0, pan=0.5):
        s = int(at * SR); e = min(N, s + len(x))
        if s < N: L[s:e] += x[: e - s] * g * (1 - pan) * 2; R[s:e] += x[: e - s] * g * pan * 2
    if b % 4 in (0,): add(k, st)
    if b % 4 == 2: add(k, st + beat * 0.5, 0.8)
    if b % 4 in (1, 3): add(sn, st, 1.0, 0.45)
    swing = 0.06 * beat
    add(hh, st, 0.9, 0.6); add(hh, st + beat / 2 + swing, 0.6, 0.62)
# vinyl-ish noise + gentle lowpass for lo-fi warmth
noise = lowpass(rng.standard_normal(N), 3000) * 0.006
L = lowpass(L, 5200) + noise; R = lowpass(R, 5200) + noise
fade = int(SR * 1.0); L[-fade:] *= np.linspace(1, 0, fade); R[-fade:] *= np.linspace(1, 0, fade)
save("trilha.wav", np.stack([L, R], 1))
print("ok")
