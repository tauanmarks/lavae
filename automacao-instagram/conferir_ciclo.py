"""Confere um ciclo sem gerar nada: regras do post.json + mídias que a API do Instagram aceita.
Usado no GitHub Actions em cada pull request de post (e pode rodar à mão).

    python automacao-instagram/conferir_ciclo.py 2026-11-16-primeira-vez-canva [outro-ciclo ...]
"""
import sys

from PIL import Image

from comum import conferir_video_reel, eh_reel, imagens, ler_post, midias, pasta_ciclo, texto_final, validar_post


def conferir(nome: str) -> list[str]:
    ciclo = pasta_ciclo(nome)
    post = ler_post(ciclo)
    erros = validar_post(post)
    if eh_reel(post):
        fs = midias(ciclo, post)
        if not fs:
            erros.append(f"vídeo {post.get('video')} não encontrado (rode criar_reel.py)")
        else:
            erros += conferir_video_reel(fs[0])
        resumo = f"reel {fs[0].stat().st_size / 1e6:.1f} MB" if fs else "reel sem vídeo"
    else:
        fs = imagens(ciclo)
        if not fs:
            erros.append("sem slides em slides/ (rode criar_post.py)")
        if fs and len(fs) != len(post.get("slides", [])):
            erros.append(f"{len(fs)} imagens em slides/, mas o post.json tem {len(post['slides'])} slides")
        for f in fs:
            im = Image.open(f)
            w, h = im.size
            if im.format != "JPEG":
                erros.append(f"{f.name}: {im.format} (a API só aceita JPEG)")
            if post.get("formato") == "stories":
                if (w, h) != (1080, 1920):
                    erros.append(f"{f.name}: {w}×{h} (story precisa 1080×1920)")
            elif not 0.8 <= w / h <= 1.91:
                erros.append(f"{f.name}: {w}×{h} fora de 4:5 a 1,91:1")
        resumo = f"{len(fs)} slides"
    if not (ciclo / "previa.jpg").exists():
        erros.append("falta previa.jpg")
    print(f"{'OK  ' if not erros else 'ERRO'} {ciclo.name}: {resumo}, legenda {len(texto_final(post))} caracteres")
    for e in erros:
        print(f"     - {e}")
    return erros


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    total = sum(len(conferir(n)) for n in sys.argv[1:])
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
