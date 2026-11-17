"""Prepara um vídeo pronto (aprovado no fluxo da Espuma) para publicar como Reels no feed.

    python automacao-instagram/criar_reel.py <ciclo> --origem CAMINHO/video.mp4 [--capa-ms 2000]

O post.json do ciclo já deve existir com "formato": "reel", legenda e hashtags.
Gera no ciclo: video.mp4 (H.264 + AAC 48 kHz, faststart, dentro dos limites da API), previa.jpg (capa + 7 quadros)
e aprovacao.html. Não altera a edição: só re-encoda para o formato que a API aceita e para caber no GitHub.
"""
import argparse
import json
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

from comum import conferir_video_reel, info_video, ler_post, pasta_ciclo, validar_post
from criar_post import pagina_aprovacao
from comum import impressao_digital

LIMITE_GITHUB = 95 * 1024 * 1024   # o GitHub recusa arquivo acima de 100 MB


def encodar(origem, destino, crf):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(origem), "-map", "0:v:0", "-map", "0:a:0",
           "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-maxrate", "12M", "-bufsize", "24M",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-g", "60", "-flags", "+cgop",
           # AAC a 128k sobe o pico real ~0,3 dB: -0,4 dB mantém o master em ≤ -1 dBTP (≈ -14,4 LUFS)
           "-af", "volume=-0.4dB", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart", "-map_metadata", "-1", str(destino)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ERRO no ffmpeg:\n" + r.stderr[-2000:])


def quadro(video, t, tamanho):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    from io import BytesIO
    return Image.open(BytesIO(r.stdout)).convert("RGB").resize(tamanho)


def folha(video, dur, capa_s, destino):
    w, h, pad = 270, 480, 12
    tempos = [capa_s] + [dur * k / 8 for k in range(1, 8)]
    img = Image.new("RGB", (4 * (w + pad) + pad, 2 * (h + pad + 30) + pad), "#D9E6F2")
    d = ImageDraw.Draw(img)
    try:
        fonte = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except OSError:
        try:
            fonte = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 20)
        except OSError:
            fonte = ImageFont.load_default()
    for k, t in enumerate(tempos):
        x, y = pad + (k % 4) * (w + pad), pad + (k // 4) * (h + pad + 30)
        img.paste(quadro(video, t, (w, h)), (x, y))
        rotulo = f"capa · {t:.1f}s" if k == 0 else f"{int(t // 60)}:{t % 60:04.1f}"
        d.text((x + 4, y + h + 4), rotulo, fill="#0E2350", font=fonte)
    img.save(destino, quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ciclo")
    ap.add_argument("--origem", required=True, help="vídeo pronto (ex.: Editor_Variado/videos-prontos/lavae-v2.mp4)")
    ap.add_argument("--capa-ms", type=int, help="quadro usado como capa no feed (milissegundos)")
    ap.add_argument("--crf", type=int, default=19)
    a = ap.parse_args()

    ciclo = pasta_ciclo(a.ciclo)
    post = ler_post(ciclo)
    if post.get("formato") != "reel":
        sys.exit('ERRO: o post.json precisa de "formato": "reel"')
    post.setdefault("video", "video.mp4")
    if a.capa_ms is not None:
        post["capa_ms"] = a.capa_ms
    erros = validar_post(post)
    if erros:
        sys.exit("ERRO no post.json:\n- " + "\n- ".join(erros))

    destino = ciclo / post["video"]
    crf = a.crf
    while True:
        encodar(a.origem, destino, crf)
        if destino.stat().st_size <= LIMITE_GITHUB or crf >= 28:
            break
        crf += 2
        print(f"  arquivo grande demais para o GitHub, refazendo com CRF {crf}…")
    erros = conferir_video_reel(destino)
    if erros:
        sys.exit("ERRO: o vídeo não atende à API:\n- " + "\n- ".join(erros))

    io = info_video(destino)
    orig = info_video(type(destino)(a.origem))
    post["video_info"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in io.items()}
    post["video_info"]["crf"] = crf
    if orig and abs(orig["duracao"] - io["duracao"]) > 0.1:
        sys.exit(f"ERRO: duração mudou no re-encode ({orig['duracao']:.2f} → {io['duracao']:.2f} s)")
    (ciclo / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=1), encoding="utf-8")

    folha(destino, io["duracao"], post.get("capa_ms", 0) / 1000, ciclo / "previa.jpg")
    digital = impressao_digital(ciclo, post)
    pagina_aprovacao(ciclo, post, digital)
    print(f"OK: {destino.name} · {io['duracao']:.1f} s · {io['bytes'] / 1e6:.1f} MB · {io['largura']}×{io['altura']} "
          f"{io['fps']:.0f} fps · CRF {crf}")
    print(f"Prévia: {ciclo / 'previa.jpg'} · aprovação: {ciclo / 'aprovacao.html'} · impressão digital {digital[:12]}")


if __name__ == "__main__":
    main()
