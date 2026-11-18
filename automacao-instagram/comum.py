"""Funções comuns do ciclo de posts (criar → aprovar → publicar)."""
import hashlib
from datetime import datetime
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]          # Publicar-lavae
AUTO = RAIZ / "automacao-instagram"
REMOTION = RAIZ / "ferramentas" / "remotion-projeto"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def pasta_ciclo(arg: str) -> Path:
    p = Path(arg)
    if not p.is_absolute() and not p.exists():
        p = AUTO / "ciclos" / arg
    p = p.resolve()
    if not (p / "post.json").exists():
        sys.exit(f"ERRO: não achei post.json em {p}")
    return p


def ler_post(ciclo: Path) -> dict:
    return json.loads((ciclo / "post.json").read_text(encoding="utf-8"))


def texto_final(post: dict) -> str:
    """Legenda exatamente como vai para o Instagram (legenda + hashtags)."""
    tags = " ".join(post.get("hashtags", []))
    return post.get("legenda", "").rstrip() + (("\n\n" + tags) if tags else "")


def eh_reel(post: dict) -> bool:
    return post.get("formato") == "reel"


def imagens(ciclo: Path) -> list[Path]:
    return sorted((ciclo / "slides").glob("slide-*.jpg"))


def midias(ciclo: Path, post: dict | None = None) -> list[Path]:
    """Arquivos que vão para o Instagram: slides (carrossel/imagem) ou o vídeo (reel)."""
    post = post if post is not None else ler_post(ciclo)
    if eh_reel(post):
        v = ciclo / post.get("video", "video.mp4")
        return [v] if v.exists() else []
    return imagens(ciclo)


def story_chamada(ciclo: Path, post: dict) -> Path | None:
    """Story 9:16 que sai logo depois do post do feed, chamando para ele ("story_chamada" no post.json)."""
    nome = post.get("story_chamada")
    return ciclo / nome if nome else None


def impressao_digital(ciclo: Path, post: dict) -> str:
    """Hash do que será publicado: mídias + legenda final (+ capa do reel). Mudou algo → aprovar de novo."""
    h = hashlib.sha256()
    for arq in midias(ciclo, post):
        h.update(arq.name.encode())
        with open(arq, "rb") as f:
            for bloco in iter(lambda: f.read(1 << 20), b""):
                h.update(bloco)
    h.update(texto_final(post).encode("utf-8"))
    chamada = story_chamada(ciclo, post)
    if chamada and chamada.exists():  # o story de chamada também é aprovado junto
        h.update(b"story_chamada:" + chamada.read_bytes())
    if eh_reel(post):
        h.update(str(post.get("capa_ms", "")).encode())
    return h.hexdigest()


# Limites da API para Reels (developers.facebook.com › IG User Media, conferido em 17/11/2026)
REEL = {"dur_min": 3, "dur_max": 15 * 60, "bytes_max": 300 * 1024 * 1024, "fps_min": 23, "fps_max": 60,
        "largura_max": 1920, "vbitrate_max": 25_000_000}


def moov_no_inicio(arq: Path) -> bool:
    """A API exige o átomo 'moov' antes do 'mdat' (faststart). Lê só os cabeçalhos dos átomos."""
    with open(arq, "rb") as f:
        while True:
            cab = f.read(8)
            if len(cab) < 8:
                return False
            tam, tipo = int.from_bytes(cab[:4], "big"), cab[4:8]
            if tipo == b"moov":
                return True
            if tipo == b"mdat":
                return False
            if tam == 1:
                tam = int.from_bytes(f.read(8), "big")
                f.seek(tam - 16, 1)
            elif tam < 8:
                return False
            else:
                f.seek(tam - 8, 1)


def info_video(arq: Path) -> dict | None:
    """ffprobe do vídeo (None se o ffprobe não estiver instalado)."""
    import shutil
    import subprocess
    if not shutil.which("ffprobe"):
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(arq)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return {"erro": r.stderr.strip()[:300]}
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), {})
    num, den = (v.get("r_frame_rate") or "0/1").split("/")
    return {"duracao": float(d["format"]["duration"]), "bytes": int(d["format"]["size"]),
            "vcodec": v.get("codec_name"), "largura": v.get("width"), "altura": v.get("height"),
            "fps": float(num) / float(den or 1), "vbitrate": int(v.get("bit_rate") or 0),
            "pix_fmt": v.get("pix_fmt"), "acodec": a.get("codec_name"),
            "arate": int(a.get("sample_rate") or 0), "acanais": a.get("channels")}


def conferir_video_reel(arq: Path) -> list[str]:
    """Regras de vídeo da API para Reels. Sem ffprobe, confere só tamanho e faststart."""
    erros = []
    if not arq.exists():
        return [f"{arq.name}: arquivo não encontrado"]
    tam = arq.stat().st_size
    if tam > REEL["bytes_max"]:
        erros.append(f"{arq.name}: {tam / 1e6:.0f} MB (máximo 300 MB)")
    if not moov_no_inicio(arq):
        erros.append(f"{arq.name}: falta faststart (átomo moov antes do mdat)")
    i = info_video(arq)
    if i is None or "erro" in i:
        return erros
    if not REEL["dur_min"] <= i["duracao"] <= REEL["dur_max"]:
        erros.append(f"duração {i['duracao']:.1f} s (Reels: 3 s a 15 min)")
    if i["vcodec"] not in ("h264", "hevc"):
        erros.append(f"vídeo em {i['vcodec']} (precisa H.264 ou HEVC)")
    if i["acodec"] != "aac" or i["arate"] > 48000:
        erros.append(f"áudio {i['acodec']} {i['arate']} Hz (precisa AAC até 48 kHz)")
    if not REEL["fps_min"] <= i["fps"] <= REEL["fps_max"]:
        erros.append(f"{i['fps']:.2f} fps (precisa 23 a 60)")
    if (i["largura"] or 0) > REEL["largura_max"]:
        erros.append(f"largura {i['largura']} px (máximo 1920)")
    if i["vbitrate"] > REEL["vbitrate_max"]:
        erros.append(f"bitrate de vídeo {i['vbitrate'] / 1e6:.1f} Mbps (máximo 25)")
    if i["pix_fmt"] not in ("yuv420p", "yuvj420p"):
        erros.append(f"pix_fmt {i['pix_fmt']} (precisa 4:2:0)")
    return erros


def validar_post(post: dict) -> list[str]:
    """Regras do Instagram e da marca. Retorna lista de problemas (vazia = ok)."""
    erros = []
    n = len(post.get("slides", []))
    if post.get("formato") == "carrossel" and not 2 <= n <= 10:
        erros.append(f"carrossel precisa de 2 a 10 slides (tem {n})")
    if eh_reel(post) and not post.get("video"):
        erros.append("reel sem o campo \"video\"")
    legenda = texto_final(post)
    if len(legenda) > 2200:
        erros.append(f"legenda com {len(legenda)} caracteres (máximo 2200)")
    if len(post.get("hashtags", [])) > 30:
        erros.append("mais de 30 hashtags")
    if legenda.count("@") > 20:
        erros.append("mais de 20 menções")
    for i, s in enumerate(post.get("slides", []), 1):
        t = s.get("titulo", s.get("frase", ""))
        if len(t) > 40:
            erros.append(f"slide {i}: título com {len(t)} caracteres (máx. 40, senão quebra em 4+ linhas)")
        if len(s.get("texto", "")) > 140:
            erros.append(f"slide {i}: texto com {len(s['texto'])} caracteres (máx. 140)")
    agenda = post.get("agendar_para")
    if agenda:
        try:
            datetime.fromisoformat(agenda)
        except ValueError:
            erros.append(f"agendar_para \"{agenda}\" fora do formato AAAA-MM-DDTHH:MM (horário de São Luís)")
    return erros
