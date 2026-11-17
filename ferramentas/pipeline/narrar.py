"""narrar.py — narração com voz neural (Microsoft Edge TTS) e tempo de cada palavra.

Uso:
  python ferramentas/pipeline/narrar.py videos-brutos/<projeto>/roteiro.json [--voz pt-BR-FranciscaNeural] [--velocidade -6%]

roteiro.json: {"voz": "...", "velocidade": "-6%", "tom": "+0Hz", "falas": [{"id": "cpf", "texto": "..."}, ...]}
Saída em videos-brutos/<projeto>/_narracao/: <id>.wav (48 kHz) e narracao.json com duração e palavras de cada fala.
Vozes femininas pt-BR: pt-BR-FranciscaNeural, pt-BR-ThalitaMultilingualNeural.
Envia só o texto do roteiro ao serviço de voz da Microsoft (precisa de internet).
"""
import argparse, asyncio, json, subprocess, sys
from pathlib import Path

import edge_tts

sys.stdout.reconfigure(encoding="utf-8")


async def falar(texto, voz, vel, tom, mp3):
    com = edge_tts.Communicate(texto, voz, rate=vel, pitch=tom, boundary="WordBoundary")
    palavras = []
    with open(mp3, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                a = ch["offset"] / 1e7
                palavras.append({"w": ch["text"], "a": round(a, 3), "b": round(a + ch["duration"] / 1e7, 3)})
    return palavras


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("--voz"); ap.add_argument("--velocidade"); ap.add_argument("--saida", default="_narracao")
    A = ap.parse_args()
    R = Path(A.roteiro).resolve()
    rot = json.loads(R.read_text(encoding="utf-8"))
    voz = A.voz or rot.get("voz", "pt-BR-FranciscaNeural")
    vel = A.velocidade or rot.get("velocidade", "-6%")
    tom = rot.get("tom", "+0Hz")
    out = R.parent / A.saida; out.mkdir(exist_ok=True)
    res = {"voz": voz, "velocidade": vel, "falas": []}
    for fala in rot["falas"]:
        mp3 = out / f"{fala['id']}.mp3"; wav = out / f"{fala['id']}.wav"
        ws = asyncio.run(falar(fala["texto"], voz, vel, tom, mp3))
        # pontuação do texto original nas palavras (o serviço devolve só a palavra)
        toks = fala["texto"].split()
        k = 0
        for w in ws:
            while k < len(toks) and w["w"].lower() not in toks[k].lower():
                k += 1
            if k < len(toks):
                w["w"] = toks[k]; k += 1
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", "48000", "-ac", "2", str(wav)], check=True)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
                                   capture_output=True, text=True).stdout)
        res["falas"].append({"id": fala["id"], "texto": fala["texto"], "duracao": round(dur, 3), "palavras": ws})
        print(f"  {fala['id']:<12} {dur:5.2f}s  {fala['texto']}")
    (out / "narracao.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ok: {out / 'narracao.json'}  (total {sum(f['duracao'] for f in res['falas']):.1f}s, voz {voz})")


if __name__ == "__main__":
    main()
