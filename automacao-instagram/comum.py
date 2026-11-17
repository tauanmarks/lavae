"""Funções comuns do ciclo de posts (criar → aprovar → publicar)."""
import hashlib
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
    return post["legenda"].rstrip() + (("\n\n" + tags) if tags else "")


def imagens(ciclo: Path) -> list[Path]:
    return sorted((ciclo / "slides").glob("slide-*.jpg"))


def impressao_digital(ciclo: Path, post: dict) -> str:
    """Hash do que será publicado: imagens + legenda final. Mudou qualquer coisa → precisa aprovar de novo."""
    h = hashlib.sha256()
    for img in imagens(ciclo):
        h.update(img.name.encode())
        h.update(img.read_bytes())
    h.update(texto_final(post).encode("utf-8"))
    return h.hexdigest()


def validar_post(post: dict) -> list[str]:
    """Regras do Instagram e da marca. Retorna lista de problemas (vazia = ok)."""
    erros = []
    n = len(post.get("slides", []))
    if post.get("formato") == "carrossel" and not 2 <= n <= 10:
        erros.append(f"carrossel precisa de 2 a 10 slides (tem {n})")
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
    return erros
