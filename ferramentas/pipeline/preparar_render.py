"""preparar_render.py — prepara um plano APROVADO para o Remotion.

Uso:  python ferramentas/pipeline/preparar_render.py videos-brutos/<projeto>/plano.json

1. Versões de trabalho dos clipes usados em remotion-projeto/public/<projeto>/<clip>.mp4:
   1080x1920, 30 fps, H.264, cor da marca, voz limpa (passa-alta + arnndn cb.rnnn + compressor leve), 48 kHz estéreo.
2. remotion-projeto/src/<projeto>/dados.json: planos com tempos de saída e legendas com tempo por palavra
   (da análise), já com as correções de transcrição do plano ("correcoes") e destaques (*palavra* na legenda).
"""
import json, re, shutil, subprocess, sys, unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
REM = RAIZ / "ferramentas" / "remotion-projeto"
FPS = 30
# cor por marca (filtros ffmpeg)
COR = {
    "prova-real": "eq=saturation=1.10:contrast=1.04:gamma=1.02,colorbalance=rm=0.03:gm=0.0:bm=-0.03",
    "mao-na-massa": "eq=saturation=1.12:contrast=1.03,colorbalance=rm=0.04:bm=-0.04",
    "diario-solto": "eq=saturation=0.95:contrast=0.96:gamma=1.03,colorbalance=rs=0.03:bs=-0.03",
    "respiro": "eq=saturation=0.9:contrast=1.02,colorbalance=rs=-0.03:bs=0.04:rh=0.04:bh=-0.03",
    "espuma": "eq=saturation=1.05:contrast=1.03:gamma=1.03,colorbalance=rs=-0.01:bs=0.02:bm=0.01",
}
VOZ = "highpass=f=80,arnndn=m=cb.rnnn,acompressor=threshold=-20dB:ratio=3:attack=10:release=200,aresample=48000"
STOP = {"a", "o", "e", "de", "do", "da", "que", "um", "uma", "é", "eu", "no", "na", "com", "pra", "por"}


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]+", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def achar(pasta, nome):
    for x in (".MOV", ".mov", ".mp4", ".MP4", ".m4v"):
        if (pasta / f"{nome}{x}").exists():
            return pasta / f"{nome}{x}"
    raise FileNotFoundError(nome)


def corrigir(palavras, correcoes):
    ws = [dict(w) for w in palavras]
    for c in correcoes:
        de = c["de"].split(); para = c["para"].split()
        i = 0
        while i <= len(ws) - len(de):
            if [w["w"] for w in ws[i:i + len(de)]] == de:
                a, b = ws[i]["a_real"], ws[i + len(de) - 1]["b_real"]
                passo = (b - a) / len(para)
                novos = [{"w": p, "a_real": round(a + k * passo, 3), "b_real": round(a + (k + 1) * passo, 3)} for k, p in enumerate(para)]
                ws[i:i + len(de)] = novos
                i += len(para)
            else:
                i += 1
    return ws


def main():
    PL = Path(sys.argv[1]).resolve()
    plano = json.loads(PL.read_text(encoding="utf-8"))
    pasta = PL.parent; proj = plano["projeto"]
    an = json.loads((pasta / "_analise" / "analise.json").read_text(encoding="utf-8"))
    clipes = {c["clip"]: c for c in an["clipes"]}
    pub = REM / "public" / proj; pub.mkdir(parents=True, exist_ok=True)
    cor = COR.get(plano["marca"], "null")

    usados = sorted({p["clip"] for p in plano["planos"] if "clip" in p} | {p["audio_clip"] for p in plano["planos"] if p.get("audio_clip")})
    for c in usados:
        out = pub / f"{c}.mp4"
        if out.exists() and out.stat().st_mtime > achar(pasta, c).stat().st_mtime:
            continue
        print(f"→ versão de trabalho {c}")
        for voz in (VOZ, VOZ.replace("arnndn=m=cb.rnnn", "afftdn=nf=-30")):  # arnndn às vezes gera NaN: cai para afftdn
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(achar(pasta, c)),
                                "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},{cor},format=yuv420p",
                                "-af", voz + ",pan=stereo|c0=c0|c1=c0", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
                               cwd=RAIZ / "ferramentas" / "modelos", capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                break
            print("  arnndn falhou, usando afftdn")
        if r.returncode:
            sys.exit(f"falhou {c}: {r.stderr[-500:]}")

    corr = {}
    for c in plano.get("correcoes", []):
        corr.setdefault(c["clip"], []).append(c)
    # narração gerada (narrar.py): copia os .wav e prepara legenda com tempo absoluto
    narr = {}
    npasta = pasta / plano.get("narracao_pasta", "_narracao")
    if (npasta / "narracao.json").exists():
        narr = {f["id"]: f for f in json.loads((npasta / "narracao.json").read_text(encoding="utf-8"))["falas"]}
        (pub / "narracao").mkdir(exist_ok=True)
        for k in narr:
            shutil.copyfile(npasta / f"{k}.wav", pub / "narracao" / f"{k}.wav")
    legenda_global, narracoes = [], []
    narr_unica = None
    if plano.get("narracao_gravada"):  # gravação alinhada (alinhar_narracao.py) substitui as falas neurais no áudio
        (pub / "narracao").mkdir(exist_ok=True)
        shutil.copyfile(pasta / plano["narracao_gravada"], pub / "narracao" / "gravada.wav")
        narr_unica = f"{proj}/narracao/gravada.wav"
    t = 0.0; saida = []
    for i, p in enumerate(plano["planos"]):
        sp = p.get("velocidade", 1) or 1
        d = p.get("duracao", (p.get("b", 0) - p.get("a", 0)) / sp)
        item = {"i": i, "tag": p.get("tag", ""), "tipo": p.get("tipo", "fala"), "t": round(t, 3), "d": round(d, 3),
                "texto_cartao": p.get("texto_cartao", ""), "palavras": [], "congelar": bool(p.get("congelar"))}
        if p.get("narracao") and p["narracao"]["id"] in narr:
            nid = p["narracao"]["id"]; ini = t + p["narracao"].get("em", 0)
            narracoes.append({"src": f"{proj}/narracao/{nid}.wav", "t": round(ini, 3), "d": narr[nid]["duracao"], "id": nid})
            ws = [{"w": w["w"], "a": round(ini + w["a"], 3), "b": round(ini + w["b"], 3), "kw": False} for w in narr[nid]["palavras"]]
            ns = [norm(w["w"]) for w in ws]; pos = 0
            for trecho in re.findall(r"\*([^*]+)\*", p.get("legenda", "")):
                alvo = [norm(x) for x in trecho.split() if norm(x)]
                achou = next((k for k in range(pos, len(ns) - len(alvo) + 1) if ns[k:k + len(alvo)] == alvo), None) if alvo else None
                if achou is not None:
                    for k in range(achou, achou + len(alvo)):
                        if alvo[k - achou] not in {norm(s) for s in STOP}:
                            ws[k]["kw"] = True
                    pos = achou + len(alvo)
            legenda_global += ws
        if "clip" in p:
            item.update({"src": f"{proj}/{p['clip']}.mp4", "a": p["a"], "b": p["b"], "vel": sp, "mudo": bool(p.get("mudo"))})
            fonte = p.get("audio_clip") or p["clip"]
            ini = p.get("audio_a", p["a"])
            if p.get("audio_clip"):
                item.update({"audioSrc": f"{proj}/{p['audio_clip']}.mp4", "audioA": p["audio_a"]})
            fim = ini + d * (1 if p.get("audio_clip") else sp)
            if p.get("tipo", "fala") == "fala":
                div = 1 if p.get("audio_clip") else sp
                for w in corrigir(clipes[fonte]["palavras"], corr.get(fonte, [])):
                    if w["a_real"] >= ini - 0.05 and w["b_real"] <= fim + 0.08:
                        item["palavras"].append({"w": w["w"], "a": round((w["a_real"] - ini) / div, 3), "b": round((w["b_real"] - ini) / div, 3), "kw": False})
                # destaque: cada trecho *...* da legenda marca a 1ª sequência igual na fala (em ordem); sem sequência exata,
                # marca só a última palavra significativa do trecho
                ns = [norm(w["w"]) for w in item["palavras"]]
                pos = 0
                for trecho in re.findall(r"\*([^*]+)\*", p.get("legenda", "")):
                    alvo = [norm(x) for x in trecho.split() if norm(x)]
                    achou = next((k for k in range(pos, len(ns) - len(alvo) + 1) if ns[k:k + len(alvo)] == alvo), None) if alvo else None
                    if achou is not None:
                        for k in range(achou, achou + len(alvo)):
                            if alvo[k - achou] not in {norm(s) for s in STOP}:
                                item["palavras"][k]["kw"] = True
                        pos = achou + len(alvo)
                    else:
                        sig = [x for x in alvo if x not in {norm(s) for s in STOP}]
                        k = next((k for k in range(pos, len(ns)) if sig and ns[k] == sig[-1]), None)
                        if k is not None:
                            item["palavras"][k]["kw"] = True; pos = k + 1
        saida.append(item); t += d
    dst = REM / "src" / proj; dst.mkdir(parents=True, exist_ok=True)
    (dst / "dados.json").write_text(json.dumps({"projeto": proj, "marca": plano["marca"], "fps": FPS, "duracao": round(t, 3), "planos": saida,
                                                "narracoes": narracoes, "narracao_unica": narr_unica, "legenda": legenda_global}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ok: {len(usados)} clipes em public/{proj}/, dados em src/{proj}/dados.json ({t:.1f}s)")


if __name__ == "__main__":
    main()
