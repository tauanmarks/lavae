"""alinhar_narracao.py — encaixa uma narração GRAVADA nos tempos das legendas (vindas da narração neural).

Uso:
  python ferramentas/pipeline/alinhar_narracao.py videos-brutos/<projeto>/plano.json <gravacao.(mp4|wav|m4a)>

Precisa antes: analisar.py na pasta da gravação (tempo por palavra) e narrar.py (legendas/tempos de referência).
Como funciona:
  1. Casa as palavras da gravação com as do roteiro (difflib), em ordem.
  2. Divide a gravação em trechos SÓ nas pausas reais da sua fala (≥ 0,15 s): nunca corta palavra.
  3. Cada trecho começa onde a 1ª palavra dele aparece na legenda; o andamento é ajustado (sem mudar o tom)
     para caber até a última palavra, limitado a 0,92x–1,12x para soar natural.
  4. Trata a voz (passa-alta, redução de ruído, EQ de presença, compressor) e grava uma faixa única do tamanho do vídeo.
Saída: <pasta da gravação>/narracao_alinhada.wav + relatório no terminal.
"""
import json, re, subprocess, sys, unicodedata, wave
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
SR = 48000
VOZ = "highpass=f=85,afftdn=nf=-28,equalizer=f=3200:t=q:w=1.2:g=2.5,equalizer=f=250:t=q:w=1:g=-2,acompressor=threshold=-22dB:ratio=3:attack=8:release=180:makeup=3"


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]+", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def ler(wav):
    with wave.open(str(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).mean(1)


def atempo(x, fator, tmp):
    """Muda a duração sem mudar o tom (ffmpeg atempo). fator > 1 acelera."""
    if abs(fator - 1) < 0.01:
        return x
    a, b = tmp / "in.wav", tmp / "out.wav"
    with wave.open(str(a), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(a), "-af", f"atempo={fator:.4f}", str(b)], check=True)
    return ler(b)


def main():
    PL = Path(sys.argv[1]).resolve(); GRAV = Path(sys.argv[2]).resolve()
    plano = json.loads(PL.read_text(encoding="utf-8")); pasta = PL.parent
    narr = {f["id"]: f for f in json.loads((pasta / plano.get("narracao_pasta", "_narracao") / "narracao.json").read_text(encoding="utf-8"))["falas"]}
    # tempos absolutos das palavras da legenda
    ref, t, total = [], 0.0, 0.0
    for p in plano["planos"]:
        sp = p.get("velocidade", 1) or 1
        d = p.get("duracao", (p.get("b", 0) - p.get("a", 0)) / sp)
        if p.get("narracao"):
            ini = t + p["narracao"].get("em", 0)
            for w in narr[p["narracao"]["id"]]["palavras"]:
                ref.append({"w": w["w"], "a": ini + w["a"], "b": ini + w["b"], "fala": p["narracao"]["id"]})
        t += d
    total = t
    an = json.loads((GRAV.parent / "_analise" / "analise.json").read_text(encoding="utf-8"))
    gw = an["clipes"][0]["palavras"]
    # 1. casamento palavra a palavra
    sm = SequenceMatcher(None, [norm(w["w"]) for w in gw], [norm(w["w"]) for w in ref], autojunk=False)
    mapa = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            mapa[blk.a + k] = blk.b + k
    print(f"palavras: gravação {len(gw)}, legenda {len(ref)}, casadas {len(mapa)}")
    # 2. trechos nas pausas da gravação
    trechos, cur = [], [0]
    for i in range(1, len(gw)):
        pausa = gw[i]["a_real"] - gw[i - 1]["b_real"]
        if pausa >= 0.15:
            trechos.append(cur); cur = []
        cur.append(i)
    trechos.append(cur)
    # áudio tratado 48 kHz
    tmp = GRAV.parent / "_tmp"; tmp.mkdir(exist_ok=True)
    limpo = tmp / "voz.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(GRAV), "-af", VOZ, "-ar", str(SR), "-ac", "1", str(limpo)], check=True)
    voz = ler(limpo)
    out = np.zeros(int((total + 1) * SR), np.float32)
    rel = []; fim_ant = 0.0
    for tr in trechos:
        cas = [i for i in tr if i in mapa]
        if not cas:
            rel.append(f"  ⚠ trecho sem correspondência na legenda: {' '.join(gw[i]['w'] for i in tr)} (fora)")
            continue
        g0 = max(0.0, gw[tr[0]]["a_real"] - 0.06); g1 = gw[tr[-1]]["b_real"] + 0.10
        r0 = ref[mapa[cas[0]]]["a"] - (gw[cas[0]]["a_real"] - g0)
        r1 = ref[mapa[cas[-1]]]["b"] + (g1 - gw[cas[-1]]["b_real"])
        fator = float(np.clip((g1 - g0) / max(0.2, r1 - r0), 0.92, 1.12))  # voz natural: no máx. 8% mais lenta / 12% mais rápida
        x = voz[int(g0 * SR):int(g1 * SR)].copy()
        n = int(0.012 * SR); x[:n] *= np.linspace(0, 1, n); x[-n:] *= np.linspace(1, 0, n)
        y = atempo(x, fator, tmp)
        ini = max(r0, fim_ant + 0.04)
        i0 = int(ini * SR); out[i0:i0 + len(y)] += y[: len(out) - i0]
        fim = ini + len(y) / SR; fim_ant = fim
        alvo_fim = ref[mapa[cas[-1]]]["b"]
        rel.append(f"  {ini:6.2f}–{fim:6.2f}  x{fator:.2f}  desvio no fim {fim - 0.10 - alvo_fim:+.2f}s  {' '.join(gw[i]['w'] for i in tr)}")
    print("\n".join(rel))
    pico = np.max(np.abs(out)) or 1
    out = out / pico * 0.89
    dst = GRAV.parent / "narracao_alinhada.wav"
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())
    print(f"ok: {dst}  ({len(trechos)} trechos, {total:.1f}s)")


if __name__ == "__main__":
    main()
