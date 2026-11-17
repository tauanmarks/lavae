"""storyboard.py — monta o storyboard de revisão a partir do plano de edição e CONFERE os cortes.

Uso:
  python ferramentas/pipeline/storyboard.py videos-brutos/<projeto>/plano.json [--previa-video]

Lê o plano.json (formato no CLAUDE.md) e, se existir, <projeto>/_analise/analise.json.
Gera em storyboards/<projeto>/:
  storyboard.html   folha para revisão e aprovação
  quadros/          3 quadros reais por plano (entrada, meio, saída)
  previa.m4a        o áudio da montagem na ordem (para ouvir se algum corte come fala)
  previa.mp4        (só com --previa-video) montagem crua em 540x960, sem grafismos
Sai com código 2 se houver alerta bloqueante (palavra cortada, frase cortada sem marcação de intencional).
"""
import argparse, html, json, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
EXT = [".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts", ".MOV", ".MP4"]
e = lambda s: html.escape(str(s))


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def fmt(t):
    m, s = divmod(max(0, t), 60)
    return f"{int(m)}:{s:04.1f}"


def achar_clip(pasta, nome):
    p = Path(nome)
    if p.is_absolute() and p.exists():
        return p
    for base in (pasta, RAIZ / "referencias", RAIZ):
        if (base / nome).exists():
            return base / nome
        for x in EXT:
            if (base / f"{nome}{x}").exists():
                return base / f"{nome}{x}"
    raise FileNotFoundError(f"clipe não encontrado: {nome}")


def conferir(planos, analise, descartados=()):
    """Retorna alertas por plano e a lista de trechos interessantes que ficaram de fora sem justificativa."""
    por_clip = {c["clip"]: c for c in (analise or {}).get("clipes", [])}
    usos = {}
    for i, p in enumerate(planos):
        p["alertas"] = []; p["ok"] = []
        if p.get("tipo") == "cartao" or "clip" not in p:
            continue
        # voz de outro clipe por cima da imagem (audio_clip/audio_a): a conferência de fala vale para o áudio
        if p.get("audio_clip"):
            sp = p.get("velocidade", 1) or 1
            c = por_clip.get(Path(p["audio_clip"]).stem)
            a = p["audio_a"]; b = a + (p["b"] - p["a"]) / sp
            vis = por_clip.get(Path(p["clip"]).stem)
            if vis:
                for (ca, cb, j) in usos.get(vis["clip"], []):
                    if p["a"] < cb - 0.05 and p["b"] > ca + 0.05:
                        p["alertas"].append(("aviso", f"imagem repete trecho já usado no plano {j + 1}"))
                usos.setdefault(vis["clip"], []).append((p["a"], p["b"], i))
        else:
            c = por_clip.get(Path(p["clip"]).stem)
            a, b = p["a"], p["b"]
        if not c:
            p["alertas"].append(("aviso", "clipe sem análise: cortes não conferidos"))
            continue
        if p.get("mudo") and not p.get("audio_clip"):
            # áudio original mudo (narração por cima): não há fala para cortar; só confere repetição de imagem
            for (ca, cb, j) in usos.get(c["clip"], []):
                if a < cb - 0.05 and b > ca + 0.05 and not p.get("reuso"):
                    p["alertas"].append(("aviso", f"repete imagem já usada no plano {j + 1}"))
            usos.setdefault(c["clip"], []).append((a, b, i))
            p["ok"].append("áudio original mudo (narração)")
            continue
        for nome, t in (("entrada", a), ("saída", b)):
            w = next((w for w in c["palavras"] if w["a_real"] + 0.02 < t < w["b_real"] - 0.02), None)
            if w:
                p["alertas"].append(("bloqueia", f"{nome} em {t:.2f}s corta a palavra “{w['w']}” ({w['a_real']:.2f}–{w['b_real']:.2f})"))
        if p.get("fala", True) and not p.get("intencional"):
            for f in c["frases"]:
                if f["a"] + 0.05 < a < f["b"] - 0.05:
                    p["alertas"].append(("bloqueia", f"começa no meio da frase “{f['texto']}”"))
                if f["a"] + 0.05 < b < f["b"] - 0.05:
                    p["alertas"].append(("bloqueia", f"termina no meio da frase “{f['texto']}”"))
        for f in c["frases"]:
            if f["a"] >= a - 0.05 and f["b"] <= b + 0.05:
                if f.get("take") == "repeticao" and not p.get("take_escolhido"):
                    p["alertas"].append(("aviso", f"usa um take marcado como repetição: “{f['texto']}” (confira se é o melhor)"))
                if f.get("take") == "falso_comeco":
                    p["alertas"].append(("aviso", f"contém falso começo: “{f['texto']}”"))
        for (ca, cb, j) in usos.get(c["clip"], []):
            if a < cb - 0.05 and b > ca + 0.05:
                p["alertas"].append(("aviso", f"repete trecho já usado no plano {j + 1}"))
        usos.setdefault(c["clip"], []).append((a, b, i))
        if not [x for x in p["alertas"] if x[0] == "bloqueia"]:
            p["ok"].append("entrada e saída em pausa, sem cortar fala")
    # interessantes fora da montagem
    fora = []
    for c in por_clip.values():
        cand = [(s["a"], s["b"], "🔊 som sem fala") for s in c.get("sons_sem_fala", [])]
        cand += [(s["a"], s["b"], "🎬 ação sem fala") for s in c.get("acao_sem_fala", [])]
        cand += [(f["a"], f["b"], f"★ frase de destaque: “{f['texto']}”") for f in c.get("frases", []) if f.get("destaque") and f.get("take") != "repeticao"]
        for a, b, o in cand:
            usado = any(a < ub and b > ua for ua, ub, _ in usos.get(c["clip"], []))
            justificado = any(Path(d.get("clip", "")).stem == c["clip"] and a < d.get("b", 0) and b > d.get("a", 0) for d in descartados)
            if not usado and not justificado:
                fora.append({"clip": c["clip"], "a": a, "b": b, "o": o})
    return fora


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plano")
    ap.add_argument("--previa-video", action="store_true")
    A = ap.parse_args()
    PL = Path(A.plano).resolve()
    plano = json.loads(PL.read_text(encoding="utf-8"))
    pasta = Path(plano.get("pasta") or PL.parent)
    proj = plano.get("projeto") or pasta.name
    OUT = RAIZ / "storyboards" / proj
    (OUT / "quadros").mkdir(parents=True, exist_ok=True)
    an_path = pasta / "_analise" / "analise.json"
    analise = json.loads(an_path.read_text(encoding="utf-8")) if an_path.exists() else None
    marcas = {m["id"]: m for m in json.loads((RAIZ / "fichas-de-marca" / "marcas.json").read_text(encoding="utf-8"))["marcas"]}
    M = marcas.get(plano.get("marca"), next(iter(marcas.values())))
    planos = plano["planos"]

    # tempos de saída
    t = 0.0
    for p in planos:
        sp = p.get("velocidade", 1) or 1
        p["d"] = round(p.get("duracao", (p.get("b", 0) - p.get("a", 0)) / sp), 3)
        p["t"] = round(t, 3); t += p["d"]
    total = t
    fora = conferir(planos, analise, plano.get("descartados", []))

    # quadros
    for i, p in enumerate(planos):
        p["quadros"] = []
        if p.get("tipo") == "cartao" or "clip" not in p:
            continue
        src = achar_clip(pasta, p["clip"])
        for k, tt in enumerate((p["a"] + 0.05, (p["a"] + p["b"]) / 2, p["b"] - 0.08)):
            q = OUT / "quadros" / f"p{i + 1:02d}_{k}.jpg"
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0, tt):.3f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "3", str(q)])
            p["quadros"].append(q.name)

    # prévia de áudio (e vídeo opcional)
    ins, idx, fa, fv, n = [], {}, "", "", 0
    for i, p in enumerate(planos):
        if p.get("tipo") == "cartao" or "clip" not in p:
            fa += f"anullsrc=r=44100:cl=stereo,atrim=0:{p['d']}[a{i}];"
            fv += f"color=c=black:s=540x960:r=30:d={p['d']}[v{i}];"
            continue
        src = str(achar_clip(pasta, p["clip"]))
        for s_ in [src] + ([str(achar_clip(pasta, p["audio_clip"]))] if p.get("audio_clip") else []):
            if s_ not in idx:
                idx[s_] = len(idx); ins += ["-i", s_]
        k = idx[src]; sp = p.get("velocidade", 1) or 1
        if p.get("congelar"):
            fv += f"[{k}:v]trim={p['a']}:{p['a'] + 0.05},setpts=PTS-STARTPTS,scale=540:960:force_original_aspect_ratio=increase,crop=540:960,fps=30,setsar=1,tpad=stop_mode=clone:stop_duration={p['d']},trim=0:{p['d']}[v{i}];"
            fa += f"anullsrc=r=44100:cl=stereo,atrim=0:{p['d']}[a{i}];"
            continue
        fv += f"[{k}:v]trim={p['a']}:{p['b']},setpts=(PTS-STARTPTS)/{sp},scale=540:960:force_original_aspect_ratio=increase,crop=540:960,fps=30,setsar=1[v{i}];"
        if p.get("audio_clip"):
            ka = idx[str(achar_clip(pasta, p["audio_clip"]))]
            fa += f"[{ka}:a]atrim={p['audio_a']}:{p['audio_a'] + p['d']:.3f},asetpts=PTS-STARTPTS,aresample=44100,aformat=channel_layouts=stereo[a{i}];"
            continue
        tempo = ""
        s = sp
        while s > 2.0:
            tempo += ",atempo=2.0"; s /= 2
        tempo += f",atempo={s:.4f}" if abs(s - 1) > 1e-3 else ""
        vol = ",volume=0" if p.get("mudo") else ""
        fa += f"[{k}:a]atrim={p['a']}:{p['b']},asetpts=PTS-STARTPTS{tempo}{vol},aresample=44100,aformat=channel_layouts=stereo[a{i}];"
    N = len(planos)
    # narração gerada (narrar.py) + música de fundo: mixadas por cima do áudio dos planos
    narr_dir = pasta / plano.get("narracao_pasta", "_narracao")
    extra_in, mix = [], []
    n0 = len(idx)
    if plano.get("narracao_gravada"):  # narração gravada já alinhada (alinhar_narracao.py): uma faixa só, desde o 0
        j = n0; extra_in += ["-i", str(pasta / plano["narracao_gravada"])]
        mix.append(f"[{j}:a]aresample=44100,aformat=channel_layouts=stereo[ngrav]")
    for i, p in enumerate(planos):
        if p.get("narracao") and not plano.get("narracao_gravada"):
            wav = narr_dir / f"{p['narracao']['id']}.wav"
            j = n0 + len(extra_in) // 2; extra_in += ["-i", str(wav)]
            ms = int((p["t"] + p["narracao"].get("em", 0)) * 1000)
            mix.append(f"[{j}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[n{i}]")
    if plano.get("musica", {}).get("arquivo"):
        j = n0 + len(extra_in) // 2; extra_in += ["-i", str(RAIZ / plano["musica"]["arquivo"])]
        vol = 10 ** (plano["musica"].get("volume_sob_fala_db", -20) / 20)
        mix.append(f"[{j}:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:{total},volume={vol:.3f}[mus]")
    ins += extra_in
    base = fa + "".join(f"[a{i}]" for i in range(N)) + f"concat=n={N}:v=0:a=1"
    if mix:
        rot = [m.rsplit("[", 1)[1][:-1] for m in mix]
        base += "[base];" + ";".join(mix) + ";[base]" + "".join(f"[{r}]" for r in rot) + f"amix=inputs={len(rot) + 1}:normalize=0:duration=first"
    fa_audio = base + "[ao]"
    r = run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fa_audio, "-map", "[ao]", "-c:a", "aac", "-b:a", "128k", str(OUT / "previa.m4a")])
    if r.returncode:
        print("aviso: prévia de áudio falhou:", r.stderr[-300:])
    if A.previa_video:
        fl = fv + "".join(f"[v{i}]" for i in range(N)) + f"concat=n={N}:v=1:a=0[vo];" + fa_audio
        r = run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fl, "-map", "[vo]", "-map", "[ao]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-c:a", "aac", str(OUT / "previa.mp4")])
        if r.returncode:
            print("aviso: prévia de vídeo falhou:", r.stderr[-300:])

    html_out = pagina(plano, M, planos, total, fora, analise is not None, A.previa_video)
    (OUT / "storyboard.html").write_text(embutir(html_out, OUT), encoding="utf-8")
    bloq = sum(1 for p in planos for a in p["alertas"] if a[0] == "bloqueia")
    avis = sum(1 for p in planos for a in p["alertas"] if a[0] == "aviso")
    print(f"ok: {OUT / 'storyboard.html'}  ({N} planos, {fmt(total)}; {bloq} bloqueios, {avis} avisos, {len(fora)} interessantes fora)")
    for i, p in enumerate(planos):
        for nivel, msg in p["alertas"]:
            print(f"  plano {i + 1}: [{nivel}] {msg}")
    sys.exit(2 if bloq else 0)


def embutir(html_txt, pasta):
    """Troca quadros/*.jpg, previa.m4a e previa.mp4 por data URIs: o HTML funciona sozinho
    (visualizador do app, e-mail, outro computador), sem depender dos arquivos ao lado."""
    import base64, re as _re
    tipos = {".jpg": "image/jpeg", ".m4a": "audio/mp4", ".mp4": "video/mp4"}
    def troca(m):
        arq = pasta / m.group(1)
        if not arq.exists():
            return m.group(0)
        return f'src="data:{tipos[arq.suffix]};base64,{base64.b64encode(arq.read_bytes()).decode()}"'
    return _re.sub(r'src="((?:quadros/[^"]+\.jpg)|previa\.m4a|previa\.mp4)"', troca, html_txt)


def pagina(plano, M, planos, total, fora, conferido, tem_video):
    C = {c["nome"]: c["hex"] for c in M["cores"]}
    cores = [c["hex"] for c in M["cores"]]
    F = M["fontes"]; cf = M["codigo"]["fontes"]
    fam = sorted({F["titulo"]["familia"], F["legenda"]["familia"], F["apoio"]["familia"], "Inter"})
    gf = "https://fonts.googleapis.com/css2?" + "&".join("family=" + f.replace(" ", "+") + ":ital,wght@0,400;0,600;0,700;0,800;1,500;1,700" if f in ("Fraunces", "Newsreader") else "family=" + f.replace(" ", "+") for f in fam) + "&display=swap"
    acc = cores[1]
    tipos_cor = {"fala": cores[1], "broll": cores[2], "cartao": cores[5 if len(cores) > 5 else 0], "acao": cores[3]}
    barra = "".join(f'<div title="{i + 1}: {e(p.get("tag") or p.get("fala") or "")}" style="flex:{max(p["d"], 0.05)};background:{tipos_cor.get(p.get("tipo", "fala"), acc)}{"" if not p["alertas"] else ";outline:2px solid #E5484D;outline-offset:-2px"}"></div>' for i, p in enumerate(planos))
    cards = []
    for i, p in enumerate(planos):
        q = p["quadros"]
        img = (f'<div class="qs"><img src="quadros/{q[1]}" alt="Plano {i + 1}, meio" class="q-main">'
               f'<div class="q-ends"><figure><img src="quadros/{q[0]}" alt="entrada"><figcaption>entra</figcaption></figure>'
               f'<figure><img src="quadros/{q[2]}" alt="saída"><figcaption>sai</figcaption></figure></div></div>') if q else f'<div class="q-card">{e(p.get("texto_cartao") or p.get("tag") or "cartão")}</div>'
        alerts = "".join(f'<li class="al {n}">{"⛔" if n == "bloqueia" else "⚠️"} {e(m)}</li>' for n, m in p["alertas"]) + "".join(f'<li class="al ok">✓ {e(m)}</li>' for m in p["ok"])
        ed = "".join(f"<li>{e(x)}</li>" for x in p.get("edicao", []))
        so = "".join(f"<li>{e(x)}</li>" for x in p.get("som", []))
        src = f'{e(p["clip"])} · {p["a"]:.2f}–{p["b"]:.2f}s' if "clip" in p else "gerado"
        if p.get("audio_clip"):
            src += f' · <b>voz:</b> {e(p["audio_clip"])} {p["audio_a"]:.2f}–{p["audio_a"] + p["d"]:.2f}s'
        vel = f' · <b>{p["velocidade"]}x</b>' if p.get("velocidade", 1) != 1 else ""
        cards.append(f"""<article class="plano">
  {img}
  <div class="info">
    <div class="ph"><span class="n">{i + 1:02d}</span><span class="tm">{fmt(p['t'])} → {fmt(p['t'] + p['d'])} · {p['d']:.1f}s</span>{f'<span class="tag">{e(p["tag"])}</span>' if p.get("tag") else ''}</div>
    <p class="src">{src}{vel} · {e(p.get('tipo', 'fala'))}</p>
    {f'<p class="fala">“{e(p["fala"])}”</p>' if p.get("fala") and isinstance(p["fala"], str) else ''}
    {f'<p class="fala">🎙️ “{e(p["narracao"].get("texto", p["narracao"]["id"]))}”</p>' if p.get("narracao") else ''}
    {f'<p class="leg"><b>Legenda:</b> {e(p["legenda"])}</p>' if p.get("legenda") else ''}
    {f'<h4>Edição</h4><ul>{ed}</ul>' if ed else ''}
    {f'<h4>Som</h4><ul>{so}</ul>' if so else ''}
    <ul class="als">{alerts}</ul>
  </div>
</article>""")
    clipes = "".join(f"<tr><td>{e(c['clip'])}</td><td><span class='uso u-{e(c.get('uso', ''))}'>{e(c.get('uso', ''))}</span></td><td>{e(c.get('motivo', ''))}</td></tr>" for c in plano.get("clipes", []))
    desc = "".join(f"<li><b>{e(d.get('clip', ''))} {d.get('a', 0):.1f}–{d.get('b', 0):.1f}s</b> {e(d.get('texto', ''))} <span class='muted'>— {e(d.get('motivo', ''))}</span></li>" for d in plano.get("descartados", []))
    fora_h = "".join(f"<li><b>{e(f['clip'])} {f['a']:.1f}–{f['b']:.1f}s</b> {e(f['o'])}</li>" for f in fora)
    pend = "".join(f"<li>{e(x)}</li>" for x in plano.get("pendencias", []))
    bloq = sum(1 for p in planos for a in p["alertas"] if a[0] == "bloqueia")
    avis = sum(1 for p in planos for a in p["alertas"] if a[0] == "aviso")
    mus = plano.get("musica", {})
    status = ("⛔ Há cortes a corrigir antes de aprovar" if bloq else "Aguardando sua aprovação")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Storyboard {e(plano.get('projeto', ''))}</title>
<link href="{gf}" rel="stylesheet">
<style>
:root {{ --bg:#F5F3EF; --surface:#fff; --fg:#17161A; --muted:#6B6772; --line:#E3DFD8; --acc:{acc}; color-scheme:light; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#121115; --surface:#1C1B21; --fg:#F2EFEA; --muted:#A6A1AD; --line:#2E2C35; color-scheme:dark; }} }}
:root[data-theme="dark"] {{ --bg:#121115; --surface:#1C1B21; --fg:#F2EFEA; --muted:#A6A1AD; --line:#2E2C35; color-scheme:dark; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 "{F['legenda']['familia']}","Inter",system-ui,sans-serif; padding:0 max(16px,env(safe-area-inset-left)); }}
.wrap {{ max-width:1120px; margin:0 auto; padding:36px 0 90px; display:grid; gap:40px; }}
h1 {{ font-family:"{F['titulo']['familia']}",serif; font-weight:{cf['tituloPeso']}; font-style:{'italic' if cf.get('tituloEstilo') == 'italic' else 'normal'}; font-size:clamp(36px,6vw,64px); line-height:1; margin:0; letter-spacing:-.02em; }}
h2 {{ font-family:"{F['titulo']['familia']}",serif; font-size:26px; margin:0 0 12px; }}
h4 {{ margin:10px 0 4px; font-size:12px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); }}
p {{ margin:0 0 6px; }} ul {{ margin:0; padding-left:18px; }}
.muted {{ color:var(--muted); }}
.status {{ display:inline-block; padding:6px 14px; border-radius:999px; font-weight:800; background:{'#E5484D' if bloq else 'var(--acc)'}; color:#fff; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }}
.stat {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:14px; }}
.stat b {{ display:block; font-size:26px; font-family:"{F['titulo']['familia']}",serif; font-variant-numeric:tabular-nums; }}
.barra {{ display:flex; height:28px; border-radius:8px; overflow:hidden; gap:2px; }}
.leg-barra {{ display:flex; gap:14px; flex-wrap:wrap; font-size:13px; color:var(--muted); margin-top:6px; }}
.leg-barra i {{ display:inline-block; width:12px; height:12px; border-radius:3px; vertical-align:-1px; margin-right:4px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:14px; }}
.plano {{ background:var(--surface); border:1px solid var(--line); border-radius:14px; overflow:hidden; display:grid; grid-template-columns:150px 1fr; min-width:0; }}
.qs {{ display:grid; gap:2px; background:#000; align-content:start; }}
.q-main {{ width:100%; aspect-ratio:9/16; object-fit:cover; display:block; }}
.q-ends {{ display:grid; grid-template-columns:1fr 1fr; gap:2px; }}
.q-ends figure {{ margin:0; position:relative; }} .q-ends img {{ width:100%; aspect-ratio:9/16; object-fit:cover; display:block; opacity:.85; }}
.q-ends figcaption {{ position:absolute; bottom:2px; left:4px; font-size:10px; color:#fff; text-shadow:0 1px 2px #000; }}
.q-card {{ aspect-ratio:9/16; display:grid; place-items:center; padding:12px; text-align:center; background:{cores[0]}; color:{cores[3] if len(cores) > 3 else '#fff'}; font-family:"{F['titulo']['familia']}",serif; font-size:20px; }}
.info {{ padding:12px 14px; min-width:0; overflow-wrap:anywhere; }}
.ph {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
.n {{ font-family:"{F['titulo']['familia']}",serif; font-size:22px; font-weight:800; color:var(--acc); }}
.tm {{ font-size:13px; font-variant-numeric:tabular-nums; color:var(--muted); }}
.tag {{ font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; background:var(--acc); color:#fff; border-radius:999px; padding:1px 8px; }}
.src {{ font-size:12px; color:var(--muted); }}
.fala {{ font-weight:700; }}
.leg {{ font-size:13px; }}
.als {{ list-style:none; padding:0; margin-top:8px; display:grid; gap:4px; }}
.al {{ font-size:12.5px; border-radius:6px; padding:3px 8px; }}
.al.bloqueia {{ background:#E5484D22; color:#C62F35; font-weight:700; }} .al.aviso {{ background:#F5A52422; }} .al.ok {{ color:#2E8B57; }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:18px; }}
.tbl {{ overflow-x:auto; }} table {{ border-collapse:collapse; width:100%; min-width:520px; font-size:14px; }}
th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
.uso {{ font-size:12px; font-weight:800; padding:2px 8px; border-radius:999px; background:var(--line); }}
.u-usado {{ background:#2E8B5733; }} .u-fora {{ background:#E5484D22; }} .u-parcial {{ background:#F5A52433; }}
.aprov {{ border:2px solid var(--acc); }}
audio, video {{ width:100%; max-width:540px; }}
@media (max-width:420px) {{ .plano {{ grid-template-columns:110px 1fr; }} }}
</style></head><body><div class="wrap">
<header style="display:grid;gap:12px">
  <span class="muted">Storyboard · marca <b>{e(M['nome'])}</b></span>
  <h1>{e(plano.get('titulo') or plano.get('projeto'))}</h1>
  <p class="muted" style="max-width:70ch">{e(plano.get('resumo', ''))}</p>
  <span class="status">{status}</span>
</header>
<div class="stats">
  <div class="stat"><b>{fmt(total)}</b>duração final</div>
  <div class="stat"><b>{len(planos)}</b>planos</div>
  <div class="stat"><b>{sum(1 for c in plano.get('clipes', []) if c.get('uso') != 'fora')}/{len(plano.get('clipes', []))}</b>clipes usados</div>
  <div class="stat"><b>{bloq}</b>cortes bloqueados</div>
  <div class="stat"><b>{avis}</b>avisos</div>
  <div class="stat"><b>{len(fora)}</b>interessantes fora</div>
</div>
<section><h2>Linha do tempo</h2><div class="barra">{barra}</div>
<div class="leg-barra"><span><i style="background:{tipos_cor['fala']}"></i>fala</span><span><i style="background:{tipos_cor['broll']}"></i>B-roll</span><span><i style="background:{tipos_cor['acao']}"></i>ação/demonstração</span><span><i style="background:{tipos_cor['cartao']}"></i>cartão</span><span>contorno vermelho = alerta</span></div></section>
<section class="card"><h2>Ouça a montagem</h2><p class="muted">Áudio na ordem dos planos, sem música: serve para conferir se algum corte come sílaba ou junta frases de forma estranha.</p>
<audio controls src="previa.m4a"></audio>{'<video controls src="previa.mp4" style="margin-top:12px"></video><p class="muted">Prévia crua 540×960 sem grafismos — não é o vídeo final.</p>' if tem_video else ''}</section>
<section><h2>Planos</h2>{'' if conferido else '<p class="al aviso">Sem análise (_analise/analise.json): cortes não foram conferidos palavra a palavra.</p>'}<div class="grid">{''.join(cards)}</div></section>
<section class="card"><h2>Clipes</h2><div class="tbl"><table><thead><tr><th>Clipe</th><th>Uso</th><th>O que entra e o que sai</th></tr></thead><tbody>{clipes}</tbody></table></div></section>
<section class="card"><h2>Trechos descartados</h2>{f'<ul>{desc}</ul>' if desc else '<p class="muted">Nenhum listado.</p>'}</section>
<section class="card"><h2>Interessantes que ficaram de fora</h2><p class="muted">Detectados na análise (som sem fala, ação sem fala, frases de destaque) e que não entraram em nenhum plano. Confira se algum merece voltar.</p>{f'<ul>{fora_h}</ul>' if fora_h else '<p class="muted">Nada ficou de fora.</p>'}</section>
<section class="card"><h2>Música e mix</h2><p><b>Faixa:</b> {e(mus.get('faixa', M['musica']['genero']))} · <b>BPM:</b> {e(mus.get('bpm', M['musica']['bpm']))} · <b>Sob a fala:</b> {e(mus.get('volume_sob_fala_db', M['musica']['volume_sob_fala_db']))} dB</p><p class="muted">{e(mus.get('notas', M['musica']['regras']))}</p></section>
{f'<section class="card"><h2>Pendências / decisões</h2><ul>{pend}</ul></section>' if pend else ''}
<section class="card aprov"><h2>Aprovação</h2><p>Revise os planos, ouça a montagem e responda no chat: <b>“aprovado”</b> para eu renderizar em <code>videos-prontos/</code>, ou diga o que mudar (ex.: “plano 4 entra mais cedo”, “troca o take do plano 7”).</p></section>
</div></body></html>"""


if __name__ == "__main__":
    main()
