"""Verifica se as imagens estão "encaixadas": nada flutuando perto da borda.

    python automacao-instagram/checar_encaixe.py ciclos/<ciclo>/slides/*.jpg [story/chamada.jpg ...]

O defeito de 20/11/2026: o Canva redimensionou o modelo de 3:4 para 4:5 e encolheu tudo. Ondas e ilustrações
que deviam sangrar até a borda passaram a terminar a 20–35 px dela, com corte reto, deixando faixas vazias.
Regra: um elemento deve ENCOSTAR na borda (sangrar) ou ficar a pelo menos ~50 px dela. Um corte reto e longo
entre 8 e 45 px da borda é erro.

Também acusa imagem que não é JPEG ou não tem o tamanho esperado (feed 1080×1350, story 1080×1920).
Saída 0 = tudo encaixado; 1 = problemas (listados).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

MIN_GAP, MAX_GAP = 8, 45      # faixa "quase encostado" (px)
MIN_RUN = 70                  # comprimento mínimo do corte reto (px)
TOLERANCIA = 2                # variação aceita da distância ao longo do corte (px)


def mascara_tinta(img: Image.Image) -> np.ndarray:
    """Pixels que não são fundo claro: cor saturada ou escura."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    sat = a.max(axis=2) - a.min(axis=2)
    lum = a.mean(axis=2)
    return (sat > 45) | (lum < 170)


def primeira_tinta(linhas: np.ndarray, limite: int) -> np.ndarray:
    """Para cada linha (vetor booleano a partir da borda), distância até o primeiro pixel de tinta que começa
    um bloco sólido de pelo menos 25 px; -1 se não houver até `limite`."""
    out = np.full(linhas.shape[0], -1)
    for i, l in enumerate(linhas):
        idx = np.flatnonzero(l[: limite + 25])
        for j in idx:
            if j > limite:
                break
            if l[j: j + 25].all():
                out[i] = j
                break
    return out


def cortes_retos(dist: np.ndarray) -> list[tuple[int, int, int]]:
    """Trechos contínuos (>= MIN_RUN) com distância estável na faixa proibida: (início, fim, distância)."""
    achados, ini = [], None
    for i in range(len(dist) + 1):
        ok = i < len(dist) and MIN_GAP <= dist[i] <= MAX_GAP
        if ok and ini is not None and abs(int(dist[i]) - int(dist[ini])) > TOLERANCIA:
            ok = False
        if ok and ini is None:
            ini = i
        elif not ok and ini is not None:
            if i - ini >= MIN_RUN:
                achados.append((ini, i - 1, int(np.median(dist[ini:i]))))
            ini = i if (i < len(dist) and MIN_GAP <= dist[i] <= MAX_GAP) else None
    return achados


def checar(arq: Path) -> list[str]:
    erros = []
    im = Image.open(arq)
    w, h = im.size
    if im.format != "JPEG":
        erros.append(f"{arq.name}: {im.format} (precisa JPEG)")
    if (w, h) not in ((1080, 1350), (1080, 1920)):
        erros.append(f"{arq.name}: {w}×{h} (feed 1080×1350, story 1080×1920)")
    m = mascara_tinta(im)
    lados = {
        "esquerda": (m, "linhas"),
        "direita": (m[:, ::-1], "linhas"),
        "topo": (m.T, "colunas"),
        "base": (m[::-1, :].T, "colunas"),
    }
    for lado, (mat, eixo) in lados.items():
        for a, b, d in cortes_retos(primeira_tinta(mat, MAX_GAP)):
            erros.append(f"{arq.name}: elemento cortado reto a {d} px da borda {lado} ({eixo} {a}–{b}); "
                         f"deve encostar na borda ou ficar a 50+ px")
    return erros


def checar_varios(arqs) -> list[str]:
    return [e for a in arqs for e in checar(Path(a))]


def main():
    arqs = [Path(a) for a in sys.argv[1:]]
    if not arqs:
        sys.exit(__doc__)
    erros = checar_varios(arqs)
    for e in erros:
        print("ERRO", e)
    print(f"{'OK' if not erros else 'FALHOU'}: {len(arqs)} imagem(ns) verificada(s), {len(erros)} problema(s)")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
