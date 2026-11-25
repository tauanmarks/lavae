"""Vídeo automático de sexta: transforma video/roteiro.json de um ciclo em Reels, com plano B garantido.

    python automacao-instagram/gerar_video.py <ciclo>          # gera e, se TUDO passar, troca o post para reel
    python automacao-instagram/gerar_video.py --pendentes      # ciclos agendados com roteiro e ainda sem resultado
    python automacao-instagram/gerar_video.py <ciclo> --teste  # gera e confere, mas não mexe no post.json

Etapas (qualquer falha = o post continua sendo o carrossel do Canva, que já está pronto e aprovado):
 1. confere o roteiro (formato, tamanhos, termos proibidos, palavras-gatilho presentes na fala);
 2. narra cada página (voz Francisca, edge-tts) e pega o tempo de cada palavra;
 3. monta o áudio (pausas entre páginas, volume padrão -16 LUFS) e calcula quando cada texto entra;
 4. mede todos os textos com a fonte de verdade (render.mjs): texto que não cabe na arte = erro;
 5. renderiza; confere o arquivo (regras da API de Reels, duração, volume, silêncios) e quadros de cada página;
 6. só então grava video.mp4, guarda o post do carrossel em post-carrossel.json, troca o post para reel,
    roda conferir_ciclo.py e registra a aprovação automática. Se a conferência final falhar, desfaz tudo.
Resultado em video/RESULTADO.md (ou video/FALHOU.md com o motivo). Saída 0 sempre que o post ficou consistente.
"""
import argparse
import asyncio
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from comum import AUTO, RAIZ, conferir_video_reel, info_video, ler_post, pasta_ciclo

PROJ = AUTO / "video-carrossel"
FUSO = timezone(timedelta(hours=-3))
SR = 48000
FALA_FINAL = "Lavaê: todos os dias, das seis e meia à meia-noite. Lavar ficou fácil!"
VOZ = "pt-BR-FranciscaNeural"
VELOCIDADE = "-4%"
INICIO = 0.3          # silêncio antes da primeira fala
PAUSA = 0.55          # entre as falas de uma página e da seguinte
CAUDA = 1.3           # depois da última fala
PROIBIDOS = ["kg", "quilo", "entrega", "delivery", "estacionamento", "wi-fi", "wifi", "passadoria", "passar a ferro",
             "promoção", "promocao", "desconto", "grátis", "gratis", "gratuit", "hipoalerg", "bebê", "bebe",
             "24 horas", "24h", "aberto 24"]


class Falha(Exception):
    pass


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def tokens(fala: str) -> list[str]:
    return [norm(t) for t in re.split(r"[\s\-–—/]+", fala) if norm(t)]


# ---------------------------------------------------------------- 1. roteiro
def conferir_roteiro(rot: dict) -> list[str]:
    e = []
    pags = rot.get("paginas")
    if not isinstance(pags, list) or len(pags) < 4:
        return ["roteiro sem 'paginas' (precisa capa, 2 a 5 dicas e final)"]
    tipos = [p.get("tipo") for p in pags]
    if tipos[0] != "capa" or tipos[-1] != "final" or any(t != "dica" for t in tipos[1:-1]) or not 2 <= len(pags) - 2 <= 5:
        e.append(f"ordem das páginas {tipos}: precisa ser capa, 2 a 5 dicas, final")
    textos_tela = []

    def item(p, campo, obj, i, maximo):
        if not isinstance(obj, dict) or not str(obj.get("texto", "")).strip():
            e.append(f"página {i}: '{campo}' sem texto")
            return
        t = obj["texto"].strip()
        textos_tela.append(t)
        if len(t) > maximo:
            e.append(f"página {i}: '{campo}' com {len(t)} caracteres (máx. {maximo}): {t!r}")
        g = obj.get("gatilho")
        if g is not None:
            if not isinstance(g, str) or len(g.split()) != 1 or not norm(g):
                e.append(f"página {i}: gatilho {g!r} de '{campo}' precisa ser UMA palavra da fala")
            elif norm(g) not in tokens(p.get("fala", "")):
                e.append(f"página {i}: gatilho {g!r} de '{campo}' não aparece na fala da página")

    for i, p in enumerate(pags, 1):
        if p.get("tipo") == "final":
            continue
        fala = str(p.get("fala", "")).strip()
        n = len(fala.split())
        if not 5 <= n <= 38:
            e.append(f"página {i}: fala com {n} palavras (5 a 38)")
        if re.search(r"\d+\s*h\s*\d+|\d+h\b", fala):
            e.append(f"página {i}: escreva horários por extenso na fala (a voz lê '6h30' errado)")
        tit = p.get("titulo")
        if not isinstance(tit, list) or not 1 <= len(tit) <= 3:
            e.append(f"página {i}: 'titulo' precisa ser lista de 1 a 3 trechos")
        else:
            for j, tr in enumerate(tit, 1):
                item(p, f"titulo[{j}]", tr, i, 28)
        if p.get("tipo") == "capa":
            sel = str(p.get("selo", "")).strip()
            if not sel or len(sel) > 18:
                e.append(f"página {i}: 'selo' da capa com 1 a 18 caracteres")
            textos_tela.append(sel)
            if p.get("subtitulo") is not None:
                item(p, "subtitulo", p["subtitulo"], i, 26)
        else:
            if p.get("selo_topo") is not None:
                item(p, "selo_topo", p["selo_topo"], i, 22)
            blocos = p.get("blocos", [])
            if not isinstance(blocos, list) or not 1 <= len(blocos) <= 4:
                e.append(f"página {i}: 'blocos' precisa ter 1 a 4 itens")
                blocos = []
            for j, b in enumerate(blocos, 1):
                lim = {"apoio": 120, "selo": 24, "check": 34}.get(b.get("tipo"))
                if lim is None:
                    e.append(f"página {i}: bloco {j} com tipo {b.get('tipo')!r} (use apoio, selo ou check)")
                else:
                    item(p, f"blocos[{j}]", b, i, lim)
    tudo = " ".join(textos_tela + [str(p.get("fala", "")) for p in pags]).lower()
    for termo in PROIBIDOS:
        if re.search(r"(?<![a-zà-ú])" + re.escape(termo), tudo):
            e.append(f"termo não permitido pelos fatos da Lavaê: {termo!r}")
    for preco in re.findall(r"r\$\s*[\d.,]+", tudo):
        if norm(preco) not in ("r1290", "r1490"):
            e.append(f"preço {preco!r} diferente de R$ 12,90 / R$ 14,90 (fatos-lavae.md)")
    return e


# ---------------------------------------------------------------- 2. narração
async def _falar(texto: str, mp3: Path):
    import edge_tts
    com = edge_tts.Communicate(texto, VOZ, rate=VELOCIDADE, boundary="WordBoundary")
    palavras = []
    with open(mp3, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                a = ch["offset"] / 1e7
                palavras.append({"w": ch["text"], "a": round(a, 3), "b": round(a + ch["duration"] / 1e7, 3)})
    return palavras


def narrar(texto: str, mp3: Path) -> list[dict]:
    for tentativa in range(3):
        try:
            ws = asyncio.run(_falar(texto, mp3))
            if ws and mp3.stat().st_size > 2000:
                return ws
        except Exception as ex:  # noqa: BLE001
            print(f"  narração falhou (tentativa {tentativa + 1}): {ex}")
    raise Falha(f"serviço de voz não respondeu para: {texto[:60]}")


def ler_audio(mp3: Path) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-f", "s16le", "-ac", "2", "-ar", str(SR), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.int16).reshape(-1, 2)


def gravar_wav(arq: Path, dados: np.ndarray):
    with wave.open(str(arq), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(dados.astype(np.int16).tobytes())


# ---------------------------------------------------------------- 3. tempos
def tempo_da_palavra(palavras: list[dict], gatilho: str, base: float, onde: str) -> float:
    alvo = norm(gatilho)
    for w in palavras:
        partes = [norm(x) for x in re.split(r"[\s\-–—/]+", w["w"])]
        if alvo in partes or norm(w["w"]) == alvo:
            return round(base + w["a"], 3)
    raise Falha(f"{onde}: a palavra-gatilho {gatilho!r} não foi encontrada na narração")


def montar(rot: dict, trab: Path) -> tuple[dict, Path]:
    pags = rot["paginas"]
    falas = [p.get("fala", "").strip() if p["tipo"] != "final" else FALA_FINAL for p in pags]
    trilhas, inicios, palavras = [], [], []
    cursor = INICIO
    for i, fala in enumerate(falas):
        mp3 = trab / f"fala-{i + 1:02d}.mp3"
        ws = narrar(fala, mp3)
        aud = ler_audio(mp3)
        # o serviço de voz deixa silêncio no começo e no fim: corta para as palavras ditas (+ respiro curto)
        corte_a = max(0.0, ws[0]["a"] - 0.08)
        corte_b = min(len(aud) / SR, ws[-1]["b"] + 0.22)
        aud = aud[int(corte_a * SR):int(corte_b * SR)]
        ws = [{**w, "a": round(w["a"] - corte_a, 3), "b": round(w["b"] - corte_a, 3)} for w in ws]
        dur = len(aud) / SR
        if not 1.0 <= dur <= 16:
            raise Falha(f"página {i + 1}: narração com {dur:.1f} s (esperado 1 a 16 s)")
        if ws[-1]["b"] > dur + 0.3:
            raise Falha(f"página {i + 1}: tempos das palavras passam do fim do áudio")
        trilhas.append(aud)
        inicios.append(cursor)
        palavras.append(ws)
        cursor += dur + (PAUSA if i < len(falas) - 1 else CAUDA)
        print(f"  página {i + 1}: {dur:5.2f} s  {fala}")
    total = cursor
    mix = np.zeros((int(total * SR) + SR, 2), dtype=np.int32)
    for aud, ini in zip(trilhas, inicios):
        k = int(ini * SR)
        mix[k:k + len(aud)] += aud
    bruto = trab / "narracao-bruta.wav"
    gravar_wav(bruto, np.clip(mix[: int(total * SR)], -32768, 32767))
    destino_pub = PROJ / "public" / "render"
    destino_pub.mkdir(parents=True, exist_ok=True)
    final = destino_pub / "narracao.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(bruto), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", str(SR), "-ac", "2", str(final)], check=True)

    # páginas: cada uma começa um pouco antes da própria fala (o deslize acontece na pausa)
    limites = [0.0] + [max(0.0, ini - 0.3) for ini in inicios[1:]] + [round(total, 3)]
    paginas = []
    for i, p in enumerate(pags):
        ini, fim, base, ws = round(limites[i], 3), round(limites[i + 1], 3), inicios[i], palavras[i]
        onde = f"página {i + 1}"
        cedo = ini + 0.15

        def quando(obj, k=0):
            g = obj.get("gatilho")
            t = tempo_da_palavra(ws, g, base, onde) if g else base + 0.15 + 0.3 * k
            return max(cedo, t)

        if p["tipo"] == "capa":
            paginas.append({"tipo": "capa", "inicio": ini, "fim": fim, "selo": p["selo"].strip(),
                            "titulo": [{"texto": tr["texto"].strip(), "destaque": bool(tr.get("destaque")), "t": quando(tr, k)}
                                       for k, tr in enumerate(p["titulo"])],
                            **({"subtitulo": {"texto": p["subtitulo"]["texto"].strip(), "t": quando(p["subtitulo"], 3)}}
                               if p.get("subtitulo") else {})})
        elif p["tipo"] == "dica":
            d = {"tipo": "dica", "inicio": ini, "fim": fim, "n": i,
                 "titulo": [{"texto": tr["texto"].strip(), "destaque": bool(tr.get("destaque")), "t": quando(tr, k)}
                            for k, tr in enumerate(p["titulo"])],
                 "blocos": [{**{k2: v for k2, v in b.items() if k2 in ("tipo", "destaque")}, "texto": b["texto"].strip(),
                             "t": quando(b, k + 2)} for k, b in enumerate(p["blocos"])]}
            if p.get("selo_topo"):
                d["selo_topo"] = {"texto": p["selo_topo"]["texto"].strip(), "t": quando(p["selo_topo"])}
            paginas.append(d)
        else:
            paginas.append({"tipo": "final", "inicio": ini, "fim": fim, "t": {
                "logo": ini + 0.05, "faixa": ini + 0.35, "cena": ini + 0.65,
                "horario": tempo_da_palavra(ws, "dias", base, onde),
                "lavar": tempo_da_palavra(ws, "lavar", base, onde),
                "facil": tempo_da_palavra(ws, "fácil", base, onde)}})
    props = {"duracao": round(total, 3), "audio": "render/narracao.wav", "paginas": paginas}
    arq = trab / "props.json"
    arq.write_text(json.dumps(props, ensure_ascii=False, indent=1), encoding="utf-8")
    return props, arq


# ---------------------------------------------------------------- 5. conferência do vídeo pronto
def ffmpeg_stderr(args: list[str]) -> str:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args, "-f", "null", "-"], capture_output=True, text=True).stderr


def quadro(video: Path, t: float) -> np.ndarray:
    from PIL import Image
    import io
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True, check=True)
    return np.asarray(Image.open(io.BytesIO(r.stdout)).convert("RGB")).astype(np.int16)


def conferir_video(video: Path, props: dict, trab: Path) -> list[str]:
    from PIL import Image
    e = list(conferir_video_reel(video))
    i = info_video(video) or {}
    if (i.get("largura"), i.get("altura")) != (1080, 1920):
        e.append(f"resolução {i.get('largura')}×{i.get('altura')} (esperado 1080×1920)")
    if abs(float(i.get("duracao", 0)) - props["duracao"]) > 0.25:
        e.append(f"duração {i.get('duracao')} s (esperado {props['duracao']} s)")
    if not 20 <= props["duracao"] <= 75:
        e.append(f"vídeo com {props['duracao']:.1f} s (o formato pede 20 a 75 s)")
    s = ffmpeg_stderr(["-i", str(video), "-map", "0:a", "-af", "ebur128"])
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", s)
    if not m:
        e.append("não consegui medir o volume do áudio")
    elif not -19 <= float(m[-1]) <= -13:
        e.append(f"volume {m[-1]} LUFS (esperado perto de -16)")
    s = ffmpeg_stderr(["-i", str(video), "-map", "0:a", "-af", "silencedetect=noise=-45dB:d=1.0"])
    for ini in re.findall(r"silence_start: (-?[\d.]+)", s):
        if float(ini) < props["duracao"] - 2.2:
            e.append(f"silêncio longo no meio da narração (a partir de {float(ini):.1f} s)")
    # quadros: cada página, já completa e antes do deslize, precisa ter a arte + os textos desenhados
    fundos = {t: np.asarray(Image.open(PROJ / "public" / "camadas" / f"fundo-{t}.png").convert("RGB")).astype(np.int16)
              for t in ("capa", "dica", "final")}
    regiao = {"capa": (82, 620, 870, 1000), "dica": (64, 300, 520, 1100), "final": (180, 560, 900, 1080)}
    for n, p in enumerate(props["paginas"], 1):
        t = p["fim"] - 0.45 if n < len(props["paginas"]) else p["fim"] - 0.2
        q = quadro(video, t)
        Image.fromarray(q.astype(np.uint8)).save(trab / f"pagina-{n:02d}.jpg", quality=88)
        if q.std() < 12:
            e.append(f"página {n}: quadro em {t:.1f} s está liso/vazio")
            continue
        x0, y0, x1, y1 = regiao[p["tipo"]]
        dif = np.abs(q[y0:y1, x0:x1] - fundos[p["tipo"]][y0:y1, x0:x1]).sum(axis=2)
        escuro = ((q[y0:y1, x0:x1].sum(axis=2) < 300) & (dif > 120)).mean()
        if escuro < 0.012:
            e.append(f"página {n}: não achei os textos desenhados no quadro de {t:.1f} s ({escuro:.3%} de texto)")
    return e


# ---------------------------------------------------------------- 6. troca para reel
def trocar_para_reel(ciclo: Path, video_tmp: Path, props: dict, trab: Path):
    post_arq, aprov = ciclo / "post.json", ciclo / "aprovacao.json"
    copia_post, copia_aprov = post_arq.read_text(encoding="utf-8"), aprov.read_text(encoding="utf-8") if aprov.exists() else None
    post = json.loads(copia_post)
    (ciclo / "post-carrossel.json").write_text(copia_post, encoding="utf-8")
    shutil.copy2(video_tmp, ciclo / "video.mp4")
    capa = props["paginas"][0]
    post.update({"formato": "reel", "video": "video.mp4", "capa_ms": int((capa["fim"] - 0.5) * 1000),
                 "video_auto": {"gerado_em": datetime.now(FUSO).isoformat(timespec="seconds"), "roteiro": "video/roteiro.json",
                                "duracao": props["duracao"], "reserva": "post-carrossel.json (carrossel do Canva)"}})
    post_arq.write_text(json.dumps(post, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, str(AUTO / "conferir_ciclo.py"), str(ciclo)], cwd=RAIZ, capture_output=True, text=True)
        print(r.stdout)
        if r.returncode != 0:
            raise Falha("conferência final do ciclo como reel falhou:\n" + r.stdout[-1500:])
        subprocess.run([sys.executable, str(AUTO / "aprovar.py"), str(ciclo), "--por",
                        "rotina automática (autorizada por tauanmarks em 18/11/2026)",
                        "--obs", "vídeo de sexta gerado e conferido por gerar_video.py"], cwd=RAIZ, check=True)
    except Exception:
        post_arq.write_text(copia_post, encoding="utf-8")
        if copia_aprov is not None:
            aprov.write_text(copia_aprov, encoding="utf-8")
        (ciclo / "video.mp4").unlink(missing_ok=True)
        (ciclo / "post-carrossel.json").unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------- execução
def gerar(nome: str, teste=False) -> bool:
    ciclo = pasta_ciclo(nome)
    pasta_v = ciclo / "video"
    rot_arq = pasta_v / "roteiro.json"
    for velho in ("RESULTADO.md", "FALHOU.md"):
        (pasta_v / velho).unlink(missing_ok=True)
    trab = ciclo / "_render"
    shutil.rmtree(trab, ignore_errors=True)
    trab.mkdir(parents=True)
    etapa = "roteiro"
    try:
        post = ler_post(ciclo)
        if not teste:
            pub = ciclo / "publicacao.json"
            if pub.exists() and json.loads(pub.read_text(encoding="utf-8")).get("id"):
                raise Falha("o post já foi publicado; nada a trocar")
            if post.get("formato") == "reel":
                raise Falha("o post já é um reel")
            ag = post.get("agendar_para")
            if ag and datetime.fromisoformat(ag).replace(tzinfo=FUSO) - datetime.now(FUSO) < timedelta(minutes=25):
                raise Falha(f"muito perto da hora de publicar ({ag}); fica o carrossel")
        rot = json.loads(rot_arq.read_text(encoding="utf-8"))
        erros = conferir_roteiro(rot)
        if erros:
            raise Falha("roteiro com problemas:\n- " + "\n- ".join(erros))
        etapa = "narração"
        print("Narrando…", flush=True)
        props, arq_props = montar(rot, trab)
        etapa = "medição dos textos"
        r = subprocess.run(["node", str(PROJ / "render.mjs"), str(arq_props), "--so-medir"], cwd=PROJ, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout[-800:], r.stderr[-2500:])
        if r.returncode != 0:
            raise Falha("texto não coube na arte:\n" + r.stderr[-2000:])
        etapa = "render"
        print("Renderizando…", flush=True)
        bruto = trab / "render.mp4"
        r = subprocess.run(["node", str(PROJ / "render.mjs"), str(arq_props), str(bruto)], cwd=PROJ, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout[-600:], r.stderr[-2000:])
        if r.returncode != 0 or not bruto.exists():
            raise Falha("o render falhou:\n" + r.stderr[-2000:])
        video = trab / "video.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(bruto), "-c", "copy", "-movflags", "+faststart", str(video)], check=True)
        etapa = "conferência do vídeo"
        erros = conferir_video(video, props, trab)
        if erros:
            raise Falha("o vídeo pronto não passou na conferência:\n- " + "\n- ".join(erros))
        if teste:
            shutil.copy2(video, pasta_v / "teste.mp4")
            print(f"TESTE OK: {pasta_v / 'teste.mp4'} (post.json não foi alterado)")
            return True
        etapa = "troca para reel"
        trocar_para_reel(ciclo, video, props, trab)
        (pasta_v / "RESULTADO.md").write_text(
            f"# Vídeo gerado e conferido\n\n{datetime.now(FUSO):%d/%m/%Y %H:%M} — {props['duracao']:.1f} s, "
            f"{len(props['paginas'])} páginas. O post agora é um reel; o carrossel do Canva ficou guardado em "
            f"`post-carrossel.json` (para voltar a ele: copie esse arquivo por cima de `post.json`, apague `video.mp4` "
            f"e rode `aprovar.py`).\n", encoding="utf-8")
        print(f"OK: {ciclo.name} virou reel ({props['duracao']:.1f} s)")
        return True
    except Exception as ex:  # noqa: BLE001  — qualquer falha: fica o carrossel
        msg = str(ex) if isinstance(ex, Falha) else f"{type(ex).__name__}: {ex}"
        (pasta_v / "FALHOU.md").write_text(
            f"# Vídeo NÃO foi usado\n\n{datetime.now(FUSO):%d/%m/%Y %H:%M} — etapa: {etapa}\n\n```\n{msg}\n```\n\n"
            f"O post continua sendo o carrossel do Canva (já conferido e aprovado). Nada precisa ser feito.\n",
            encoding="utf-8")
        print(f"::warning::{ciclo.name}: vídeo não usado ({etapa}): {msg[:400]}")
        return False
    finally:
        shutil.rmtree(PROJ / "public" / "render", ignore_errors=True)


def pendentes() -> list[str]:
    hoje = datetime.now(FUSO).date()
    nomes = []
    for d in sorted((AUTO / "ciclos").iterdir()):
        if not (d / "video" / "roteiro.json").exists() or not (d / "post.json").exists():
            continue
        if (d / "video" / "RESULTADO.md").exists() or (d / "video" / "FALHOU.md").exists():
            continue
        post = ler_post(d)
        ag = post.get("agendar_para")
        if post.get("formato") == "reel" or not ag or datetime.fromisoformat(ag).date() < hoje:
            continue
        nomes.append(d.name)
    return nomes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ciclo", nargs="?")
    ap.add_argument("--pendentes", action="store_true")
    ap.add_argument("--teste", action="store_true")
    ap.add_argument("--exemplo", action="store_true",
                    help="teste completo com video-carrossel/exemplo-roteiro.json numa cópia do último ciclo (não mexe em nada)")
    a = ap.parse_args()
    if a.exemplo:
        base = sorted(d for d in (AUTO / "ciclos").iterdir() if (d / "post.json").exists() and (d / "story").exists())[-1]
        tmp = RAIZ / "_teste-video"
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(base, tmp, ignore=shutil.ignore_patterns("publicacao.json", "video", "_render"))
        (tmp / "video").mkdir()
        shutil.copy2(PROJ / "exemplo-roteiro.json", tmp / "video" / "roteiro.json")
        ok = gerar(str(tmp), teste=True)
        sys.exit(0 if ok else 1)
    nomes = pendentes() if a.pendentes else [a.ciclo] if a.ciclo else []
    if not nomes:
        print("Nenhum vídeo para gerar.")
        return
    for n in nomes:
        print(f"== {n}", flush=True)
        gerar(n, teste=a.teste)


if __name__ == "__main__":
    main()
