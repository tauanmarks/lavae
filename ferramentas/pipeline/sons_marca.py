"""sons_marca.py — kit sonoro próprio de cada marca (efeitos + trilha), sintetizado do zero (sem direitos autorais).

Uso:
  python ferramentas/pipeline/sons_marca.py                 # todas as marcas, trilha de 60 s
  python ferramentas/pipeline/sons_marca.py caos-bom 45     # uma marca, trilha de 45 s
Saída: ferramentas/sons/<marca>/*.wav  (48 kHz estéreo, pico -1 dB)

As trilhas são "camas" simples no BPM e clima da marca. Para trilhas de qualidade comercial,
coloque faixas livres de direitos em referencias/musicas/<marca>/ — o editor usa essas primeiro.
"""
import shutil, sys, wave
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
SR = 48000
rng = np.random.default_rng(11)


def t(d): return np.arange(int(SR * d)) / SR
def midi(m): return 440 * 2 ** ((m - 69) / 12)
def noise(d): return rng.standard_normal(int(SR * d))


def filt(x, lo=None, hi=None):
    """Filtro de 2ª ordem aproximado no domínio da frequência. lo = passa-alta, hi = passa-baixa (Hz)."""
    n = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR) + 1e-6
    H = np.ones_like(f)
    if hi: H /= np.sqrt(1 + (f / hi) ** 4)
    if lo: H /= np.sqrt(1 + (lo / f) ** 4)
    return np.fft.irfft(X * H, n)


def mx(*xs):
    """Soma sinais de tamanhos diferentes (alinhados no início)."""
    out = np.zeros(max(len(x) for x in xs))
    for x in xs:
        out[: len(x)] += x
    return out


def env(d, a=0.005, decay=8.0):
    tt = t(d); return np.minimum(1, tt / max(a, 1e-4)) * np.exp(-tt * decay)


def sweep(f0, f1, d, curva=3.0):
    tt = t(d); f = f1 + (f0 - f1) * np.exp(-tt * curva / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def reverb(x, tam=0.35, mix=0.25):
    ir = noise(tam) * np.exp(-t(tam) * 9); ir = filt(ir, hi=6000)
    y = np.convolve(x, ir)[: len(x) + int(SR * tam)] if len(x) < SR * 3 else np.real(np.fft.irfft(np.fft.rfft(x, len(x) + len(ir)) * np.fft.rfft(ir, len(x) + len(ir))))
    y = y / (np.max(np.abs(y)) + 1e-9) * np.max(np.abs(x))
    out = np.zeros(len(y)); out[: len(x)] += x * (1 - mix); out += y * mix
    return out


def save(pasta, nome, x):
    x = np.asarray(x, np.float64)
    if x.ndim == 1: x = np.stack([x, x], 1)
    x = x / (np.max(np.abs(x)) or 1) * 0.89
    with wave.open(str(pasta / nome), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------ efeitos
SFX = {
    "pop": lambda: sweep(900, 260, 0.12, 4) * env(0.12, 0.001, 38),
    "clique": lambda: np.concatenate([filt(noise(0.03), lo=1500) * env(0.03, 0.0005, 260) + np.sin(2 * np.pi * 3200 * t(0.03)) * env(0.03, 0.0005, 200) * 0.6, np.zeros(800)]),
    "tick": lambda: np.sin(2 * np.pi * 2400 * t(0.06)) * env(0.06, 0.0005, 90) + filt(noise(0.06), lo=4000) * env(0.06, 0.0005, 300) * 0.3,
    "check": lambda: np.concatenate([np.sin(2 * np.pi * 1320 * t(0.07)) * env(0.07, 0.001, 40), np.sin(2 * np.pi * 1980 * t(0.25)) * env(0.25, 0.001, 14)]),
    "ding": lambda: sum(a * np.sin(2 * np.pi * 1568 * m * t(1.2)) * env(1.2, 0.002, 3 + m) for m, a in [(1, 1), (2.76, .3), (5.4, .12)]),
    "whoosh": lambda: (lambda d: filt(noise(d), lo=300, hi=3500) * np.sin(np.pi * np.clip(t(d) / d, 0, 1)) ** 2)(0.5),
    "swoosh": lambda: (lambda d: filt(noise(d), lo=800, hi=6000) * np.sin(np.pi * np.clip(t(d) / d, 0, 1)) ** 3)(0.25),
    "swoosh_macio": lambda: (lambda d: filt(noise(d), lo=200, hi=1800) * np.sin(np.pi * np.clip(t(d) / d, 0, 1)) ** 2)(0.6),
    "teclado": lambda: np.concatenate([np.concatenate([filt(noise(0.02), lo=2000, hi=8000) * env(0.02, 0.0005, 250) * rng.uniform(.5, 1), np.zeros(int(SR * rng.uniform(.06, .14)))]) for _ in range(9)]),
    "carimbo": lambda: mx(sweep(160, 50, 0.35, 5) * env(0.35, 0.001, 12), filt(noise(0.08), hi=1500) * env(0.08, 0.001, 50) * 0.8),
    "caixa": lambda: np.concatenate([filt(noise(0.05), lo=2000) * env(0.05, 0.001, 80) * .5, sum(np.sin(2 * np.pi * f * t(0.9)) * env(0.9, 0.002, 5) for f in (2093, 2637))]),
    "buzzer": lambda: np.sign(np.sin(2 * np.pi * 140 * t(0.35))) * filt(np.ones(int(SR * .35)), hi=2) * 0.5 * env(0.35, 0.005, 3),
    "boom": lambda: reverb(mx(sweep(110, 35, 1.2, 4) * env(1.2, 0.002, 3.5), filt(noise(0.1), hi=800) * env(0.1, 0.001, 40) * 0.6), 0.6, 0.2),
    "scratch": lambda: filt(noise(0.35), lo=400, hi=3000) * np.abs(np.sin(2 * np.pi * 9 * t(0.35))) * env(0.35, 0.01, 4) + sweep(1200, 200, 0.35, 2) * 0.3 * env(0.35, 0.01, 5),
    "bonk": lambda: sweep(600, 180, 0.25, 6) * env(0.25, 0.001, 20) + np.sin(2 * np.pi * 1350 * t(0.25)) * env(0.25, 0.001, 30) * 0.4,
    "riser": lambda: (lambda d: filt(noise(d), lo=500, hi=7000) * (t(d) / d) ** 2 + sweep(200, 1600, d, -1) * (t(d) / d) ** 2 * 0.25)(1.0),
    "obturador": lambda: np.concatenate([filt(noise(0.03), lo=1000) * env(0.03, 0.0005, 150), np.zeros(int(SR * .05)), filt(noise(0.04), lo=600) * env(0.04, 0.0005, 120)]),
    "tape_stop": lambda: (lambda d: np.sin(2 * np.pi * np.cumsum(np.linspace(330, 20, int(SR * d)) ) / SR) * np.linspace(1, 0, int(SR * d)) + 0.5 * np.sin(2 * np.pi * np.cumsum(np.linspace(220, 15, int(SR * d))) / SR) * np.linspace(1, 0, int(SR * d)))(0.7),
    "papel": lambda: (lambda d: filt(noise(d), lo=1500, hi=9000) * np.sin(np.pi * np.clip(t(d) / d, 0, 1)) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 23 * t(d)))))(0.4),
    "relogio": lambda: np.concatenate([np.concatenate([np.sin(2 * np.pi * f * t(0.04)) * env(0.04, 0.0005, 120), np.zeros(int(SR * .46))]) for f in (2600, 2000, 2600, 2000)]),
    "sub_drop": lambda: sweep(90, 30, 1.0, 3) * env(1.0, 0.003, 3),
    "shimmer": lambda: sum(np.sin(2 * np.pi * rng.uniform(2500, 6000) * t(1.2)) * env(1.2, rng.uniform(0.05, 0.5), 5) * rng.uniform(.2, .6) for _ in range(12)),
    "impacto_suave": lambda: reverb(sweep(140, 55, 0.8, 4) * env(0.8, 0.004, 5), 0.8, 0.35),
    "tampa": lambda: filt(noise(0.04), lo=900, hi=5000) * env(0.04, 0.0005, 160) + sweep(700, 400, 0.04, 3) * env(0.04, 0.0005, 120) * 0.5,
    "coracao": lambda: np.concatenate([sweep(70, 40, 0.15, 4) * env(0.15, 0.003, 25), np.zeros(int(SR * .08)), sweep(65, 38, 0.15, 4) * env(0.15, 0.003, 25) * .7, np.zeros(int(SR * .5))]),
    "respiracao": lambda: (lambda d: filt(noise(d), lo=400, hi=2500) * np.sin(np.pi * np.clip(t(d) / d, 0, 1)) ** 1.5 * 0.5)(1.4),
    "whoosh_reverb": lambda: reverb((lambda d: filt(noise(d), lo=300, hi=4000) * np.sin(np.pi * np.clip(t(d) / d, 0, 1)) ** 2)(0.6), 1.2, 0.45),
    "timer": lambda: np.concatenate([sum(np.sin(2 * np.pi * 2093 * m * t(0.18)) * env(0.18, 0.001, 12) for m in (1, 2.01)), np.zeros(int(SR * .08))] * 3),
    "bolha": lambda: sweep(500, 1400, 0.09, -2) * env(0.09, 0.004, 30) * 0.8,
    "clique_suave": lambda: filt(np.sin(2 * np.pi * 1800 * t(0.05)) * env(0.05, 0.001, 70) + noise(0.05) * env(0.05, 0.0005, 300) * 0.2, hi=4000),
    "ding_suave": lambda: reverb(sum(a * np.sin(2 * np.pi * f0 * t(1.6)) * env(1.6, 0.004, 2.5) for f0, a in [(1046.5, 1), (1568, 0.5), (2093, 0.2)]), 1.0, 0.35),
    "tic_tac": lambda: np.concatenate([np.concatenate([filt(noise(0.015), lo=3000) * env(0.015, 0.0005, 300), np.zeros(int(SR * .235))]) for _ in range(8)]),
}

KITS = {
    "passo-claro": ["clique", "check", "swoosh", "ding", "teclado", "pop"],
    "prova-real": ["carimbo", "caixa", "pop", "buzzer", "swoosh", "whoosh"],
    "diario-solto": ["obturador", "swoosh_macio", "tape_stop", "pop"],
    "caos-bom": ["boom", "scratch", "bonk", "riser", "swoosh", "pop"],
    "ponto-chave": ["relogio", "papel", "pop", "sub_drop", "tick"],
    "vitrine": ["shimmer", "whoosh", "tampa", "impacto_suave"],
    "respiro": ["coracao", "respiracao", "whoosh_reverb", "boom"],
    "mao-na-massa": ["pop", "timer", "tic_tac", "swoosh"],
    "espuma": ["bolha", "clique_suave", "ding_suave", "swoosh_macio"],
}


# ------------------------------------------------------------------ trilhas
class Mix:
    def __init__(s, d): s.N = int(SR * d); s.L = np.zeros(s.N); s.R = np.zeros(s.N)
    def add(s, x, at, g=1.0, pan=0.5):
        i = int(at * SR)
        if i >= s.N: return
        j = min(s.N, i + len(x)); s.L[i:j] += x[: j - i] * g * (1 - pan) * 2; s.R[i:j] += x[: j - i] * g * pan * 2


def epiano(f, d):
    tt = t(d); e_ = (1 - np.exp(-tt * 60)) * np.exp(-tt * 1.3)
    return (np.sin(2 * np.pi * f * tt) + .25 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 4)) * e_ * (1 + .08 * np.sin(2 * np.pi * 4.5 * tt))


_PLUCK = {}
def pluck(f, d, brilho=3000):
    """Corda dedilhada (violão/nylon): harmônicos que decaem mais rápido quanto mais agudos + ataque de ruído."""
    key = (round(f, 2), round(d, 3), brilho)
    if key not in _PLUCK:
        tt = t(d)
        x = sum((1 / h) * np.sin(2 * np.pi * h * f * tt) * np.exp(-tt * (1.8 + 0.9 * h)) for h in range(1, 11) if h * f < brilho * 1.5)
        x = x + filt(noise(d), lo=1000, hi=brilho) * np.exp(-tt * 80) * .15
        _PLUCK[key] = x * np.minimum(1, tt / 0.002)
    return _PLUCK[key]


def pad(fs, d, brilho=1800):
    tt = t(d); x = sum(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) + .5 * np.sin(2 * np.pi * f * 1.003 * tt) for f in fs)
    a = np.minimum(1, tt / (d * .3)) * np.minimum(1, (d - tt) / (d * .3))
    return filt(x * a, hi=brilho) / len(fs)


def saw(f, d):
    tt = t(d); return 2 * ((f * tt) % 1) - 1


KICK = lambda: sweep(150, 45, 0.35, 5) * env(0.35, 0.001, 9)
SNARE = lambda: filt(noise(0.2), lo=300, hi=6000) * env(0.2, 0.001, 22) * .6 + np.sin(2 * np.pi * 190 * t(0.2)) * env(0.2, 0.001, 30) * .4
def CLAP():
    n = int(SR * .2); out = np.zeros(n)
    for k in range(3):
        x = filt(noise(0.15), lo=800, hi=5000) * env(0.15, 0.001, 30); o = int(SR * k * .011)
        out[o:o + len(x)] += x[: n - o]
    return out
HAT = lambda: filt(noise(0.05), lo=7000) * env(0.05, 0.0005, 90)
RIM = lambda: np.sin(2 * np.pi * 1700 * t(0.04)) * env(0.04, 0.0005, 120) + filt(noise(0.04), lo=2000) * env(0.04, 0.0005, 200) * .4
SHAKER = lambda: filt(noise(0.08), lo=5000) * np.sin(np.pi * np.clip(t(0.08) / .08, 0, 1)) * .5
SUB808 = lambda f, d: np.sin(2 * np.pi * np.cumsum(np.full(int(SR * d), f)) / SR) * env(d, 0.002, 1.2) * (1 + 0.3 * env(d, 0.001, 30))

# progressões (MIDI) por estilo
PROG = {
    "lofi": [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]],
    "indie": [[48, 55, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]],
    "groove": [[50, 57, 60, 65], [55, 59, 62, 65], [52, 55, 59, 62], [57, 61, 64, 67]],
    "trap": [[45, 48, 52], [41, 45, 48], [43, 47, 50], [40, 43, 47]],
    "ambient": [[48, 55, 62, 64], [45, 52, 57, 64], [41, 48, 55, 60], [43, 50, 55, 62]],
    "house": [[45, 52, 55, 60], [41, 48, 52, 57], [48, 52, 55, 62], [43, 50, 55, 59]],
    "cinema": [[45, 52, 57, 60], [41, 48, 53, 57], [48, 55, 60, 64], [43, 50, 55, 59]],
    "bossa": [[50, 53, 57, 60, 64], [55, 59, 62, 65], [48, 52, 55, 59, 62], [57, 60, 64, 67]],
    "relax": [[48, 55, 59, 64], [45, 52, 55, 60], [41, 48, 52, 57], [43, 50, 55, 59]],
}
ESTILO = {"passo-claro": ("lofi", 95), "prova-real": ("groove", 110), "diario-solto": ("indie", 88), "caos-bom": ("trap", 140),
          "ponto-chave": ("ambient", 80), "vitrine": ("house", 116), "respiro": ("cinema", 70), "mao-na-massa": ("bossa", 108),
          "espuma": ("relax", 72)}


def trilha(marca, dur):
    est, bpm = ESTILO[marca]; beat = 60 / bpm; bar = beat * 4; M = Mix(dur); P = PROG[est]
    nbar = int(dur / bar) + 1
    k, sn, cl, hh, rim, sh = KICK(), SNARE(), CLAP(), HAT(), RIM(), SHAKER()
    for b in range(nbar):
        st = b * bar; ch = P[(b // 2) % 4] if est not in ("cinema", "ambient") else P[b % 4]
        sec = b / max(1, nbar - 1)  # 0..1 ao longo da faixa
        if est in ("lofi", "indie"):
            for hit in (0, 2.5):
                for j, m in enumerate(ch):
                    x = (epiano(midi(m), bar * .9) if est == "lofi" else pluck(midi(m), bar * .9, 2600)) * .16
                    M.add(x, st + hit * beat + j * (0.012 if est == "lofi" else 0.03), 1, .35 + .1 * j)
            M.add(np.sin(2 * np.pi * midi(ch[0] - 12) * t(bar * .9)) * env(bar * .9, 0.01, 1.6) * .35, st)
            for q in range(4):
                if q in (0,) or (q == 2 and est == "indie"): M.add(k, st + q * beat, .9)
                if q == 2 and est == "lofi": M.add(k, st + q * beat + beat / 2, .7)
                if q in (1, 3): M.add(sn if est == "lofi" else rim, st + q * beat, .8 if est == "lofi" else .5, .45)
                M.add(hh, st + q * beat, .45, .6); M.add(hh if est == "lofi" else sh, st + q * beat + beat / 2 + .06 * beat, .3, .62)
        elif est == "groove":
            for q in range(4):
                M.add(k, st + q * beat, .9 if q in (0, 2) else .0)
                if q in (1, 3): M.add(cl, st + q * beat, .7, .5)
                for s16 in range(4): M.add(hh, st + q * beat + s16 * beat / 4, .25 if s16 % 2 else .4, .6)
            for s16, nota in enumerate([0, None, 12, None, 0, 0, None, 10, None, 0, 12, None, 7, None, 0, None]):
                if nota is not None: M.add(filt(saw(midi(ch[0] - 24 + nota), beat / 4 * .9), hi=900) * env(beat / 4 * .9, 0.002, 6) * .5, st + s16 * beat / 4)
            for hit in (1.5, 3.5):
                for j, m in enumerate(ch): M.add(filt(saw(midi(m + 12), .12), hi=2500) * env(.12, 0.001, 18) * .12, st + hit * beat, 1, .3 + .13 * j)
        elif est == "trap":
            M.add(SUB808(midi(ch[0] - 12), bar * .95) * .7, st)
            M.add(k, st); M.add(k, st + 2.5 * beat, .8)
            M.add(cl, st + 2 * beat, .8)
            for s in range(16 if b % 2 == 0 else 24):
                step = bar / (16 if b % 2 == 0 else 24); M.add(hh, st + s * step, .3 if s % 2 else .45, .6)
            for j, nota in enumerate([0, 3, 7, 3] * 2):
                M.add(np.sin(2 * np.pi * midi(ch[0] + 24 + nota) * t(beat / 2 * .8)) * env(beat / 2 * .8, .003, 7) * .16, st + j * beat / 2, 1, .4)
        elif est == "ambient":
            M.add(pad([midi(m) for m in ch], bar * 1.2, 1400) * .5, st)
            for j in range(3):
                if rng.random() < .7: M.add(epiano(midi(ch[(j * 2) % len(ch)] + 12), beat * 3) * .12, st + j * beat * 1.33, 1, .3 + .2 * j)
            if b >= 2: M.add(k, st, .35); M.add(hh, st + 2 * beat, .2, .6)
        elif est == "house":
            M.add(pad([midi(m) for m in ch], bar, 2200) * .35, st)
            for q in range(4):
                M.add(k, st + q * beat, .9)
                M.add(hh, st + q * beat + beat / 2, .45, .62)
                if q in (1, 3): M.add(cl, st + q * beat, .45)
                M.add(np.sin(2 * np.pi * midi(ch[0] - 12) * t(beat / 2 * .9)) * env(beat / 2 * .9, .003, 4) * .45, st + q * beat + beat / 2)
        elif est == "cinema":
            ganho = .35 + .65 * sec
            M.add(pad([midi(m) for m in ch] + [midi(ch[0] - 12)], bar * 1.15, 900 + 2000 * sec) * .6 * ganho, st)
            for j in range(8):
                m = ch[[0, 1, 2, 3, 2, 1, 2, 3][j]] + 12
                M.add(epiano(midi(m), beat * 1.5) * .14, st + j * beat / 2, 1, .35 + .04 * j)
            if sec > .6: M.add(sweep(70, 40, 1.0, 3) * env(1, .004, 2) * .5 * sec, st)
        elif est == "relax":
            # pad longo e macio + sinos esparsos (pentatônica) + textura de água; sem bateria
            M.add(pad([midi(m) for m in ch] + [midi(ch[0] - 12)], bar * 1.25, 1100) * 0.55, st)
            for j in range(4):
                if rng.random() < 0.55:
                    nota = ch[0] + 24 + [0, 2, 4, 7, 9, 12][int(rng.integers(0, 6))]
                    sino = sum(a * np.sin(2 * np.pi * midi(nota) * m_ * t(3.0)) * env(3.0, 0.01, 1.4 + m_) for m_, a in [(1, 1), (2.0, .25), (3.01, .08)])
                    M.add(sino * 0.07, st + j * beat + rng.uniform(0, beat * 0.5), 1, rng.uniform(.25, .75))
        elif est == "bossa":
            for s16 in (0, 3, 6, 10, 12):
                for j, m in enumerate(ch): M.add(pluck(midi(m), beat * .8, 2200) * .13, st + s16 * beat / 4 + j * .012, 1, .3 + .1 * j)
            for q, nota in ((0, 0), (1.5, 7), (2, 0), (3.5, 7)):
                M.add(np.sin(2 * np.pi * midi(ch[0] - 12 + nota) * t(beat * .9)) * env(beat * .9, .005, 3) * .4, st + q * beat)
            for q in range(4):
                M.add(rim, st + q * beat + (beat * .75 if q % 2 else 0), .35, .4)
                M.add(sh, st + q * beat, .25, .65); M.add(sh, st + q * beat + beat / 2, .35, .65)
            M.add(k, st, .5); M.add(k, st + 2 * beat, .4)
    L, R = M.L, M.R
    if est in ("lofi", "indie"):
        nz = filt(noise(dur), hi=3000)[: M.N] * .004; L = filt(L, hi=5200) + nz; R = filt(R, hi=5200) + nz
    if est == "relax":  # água corrente bem baixa, ondulando devagar
        agua = filt(noise(dur), lo=300, hi=2200)[: M.N] * (0.012 + 0.006 * np.sin(2 * np.pi * 0.07 * t(dur)[: M.N]))
        L = filt(L, hi=6000) + agua; R = filt(R, hi=6000) + np.roll(agua, 900)
    f = int(SR * 1.5); L[-f:] *= np.linspace(1, 0, f); R[-f:] *= np.linspace(1, 0, f)
    fi = int(SR * .3); L[:fi] *= np.linspace(0, 1, fi); R[:fi] *= np.linspace(0, 1, fi)
    return np.stack([L, R], 1)


def main():
    alvo = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].replace(".", "").isdigit() else None
    dur = float(next((a for a in sys.argv[1:] if a.replace(".", "").isdigit()), 60))
    for marca, kit in KITS.items():
        if alvo and marca != alvo:
            continue
        pasta = RAIZ / "ferramentas" / "sons" / marca; pasta.mkdir(parents=True, exist_ok=True)
        for s in kit:
            save(pasta, f"{s}.wav", SFX[s]())
        save(pasta, "trilha.wav", trilha(marca, dur))
        est, bpm = ESTILO[marca]
        # cópia para o Remotion (staticFile("sons/<marca>/<efeito>.wav"))
        pub = RAIZ / "ferramentas" / "remotion-projeto" / "public" / "sons" / marca
        pub.mkdir(parents=True, exist_ok=True)
        for f in pasta.glob("*.wav"):
            shutil.copyfile(f, pub / f.name)
        print(f"ok: {marca}: {len(kit)} efeitos + trilha {est} {bpm} BPM ({dur:.0f}s)")


if __name__ == "__main__":
    main()
