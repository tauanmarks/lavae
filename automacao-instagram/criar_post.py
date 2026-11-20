"""Cria as imagens do carrossel (Remotion, marca Espuma) e a página de aprovação de um ciclo.

    python automacao-instagram/criar_post.py 2026-11-16-primeira-vez

Saída no ciclo: slides/slide-01.jpg… (1080×1350, JPEG — o único formato de imagem aceito pela API),
aprovacao.html (para revisar) e a impressão digital do que foi gerado. Não publica nada.
"""
import base64
import html
import json
import shutil
import subprocess
import sys
from datetime import datetime

from PIL import Image

import checar_encaixe
from comum import REMOTION, impressao_digital, imagens, ler_post, pasta_ciclo, story_chamada, texto_final, validar_post


def renderizar(ciclo, post):
    tmp = ciclo / "_render"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    props = tmp / "props.json"
    props.write_text(json.dumps({"slides": post["slides"]}, ensure_ascii=False), encoding="utf-8")
    cmd = ["npx", "remotion", "render", "CarrosselEspuma", str(tmp / "png"), "--sequence", "--image-format=png",
           f"--props={props}", "--log=error"]
    r = subprocess.run(cmd, cwd=REMOTION, shell=(sys.platform == "win32"), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit("ERRO no render do Remotion:\n" + (r.stderr or r.stdout)[-3000:])
    pngs = sorted((tmp / "png").glob("*.png"))
    if len(pngs) != len(post["slides"]):
        sys.exit(f"ERRO: esperava {len(post['slides'])} imagens, o Remotion gerou {len(pngs)}")
    destino = ciclo / "slides"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir()
    for k, p in enumerate(pngs, 1):
        im = Image.open(p).convert("RGB")
        if im.size != (1080, 1350):
            sys.exit(f"ERRO: {p.name} saiu {im.size}, esperado 1080×1350")
        im.save(destino / f"slide-{k:02d}.jpg", "JPEG", quality=93, optimize=True, subsampling=0)
    shutil.rmtree(tmp)


def conferir_slides_prontos(ciclo, post):
    """Slides exportados de fora (Canva): não renderiza, só confere o que a API do Instagram exige.
    O modelo do Canva é 3:4 (1080×1440), que a API recusa: aqui ele é cortado para 4:5 (1080×1350), tirando 45 px
    de cima e de baixo. NUNCA redimensione o design no Canva (resize-design desencaixa tudo: defeito de 20/11/2026).
    No fim, roda checar_encaixe.py (nada flutuando perto da borda)."""
    fs = imagens(ciclo)
    for f in fs:
        im = Image.open(f)
        if im.size == (1080, 1440):
            im.convert("RGB").crop((0, 45, 1080, 1395)).save(f, "JPEG", quality=92)
            print(f"{f.name}: 1080×1440 cortado para 1080×1350")
    erros = []
    if len(fs) != len(post["slides"]):
        erros.append(f"{len(fs)} imagens em slides/, mas o post.json tem {len(post['slides'])} slides")
    for f in fs:
        im = Image.open(f)
        if im.format != "JPEG":
            erros.append(f"{f.name}: {im.format}, a API só aceita JPEG")
        w, h = im.size
        if not 0.8 <= w / h <= 1.91:
            erros.append(f"{f.name}: {w}×{h} fora da faixa 4:5 a 1,91:1 aceita pela API (3:4 é recusado)")
        elif (w, h) != (1080, 1350):
            print(f"Aviso: {f.name} tem {w}×{h} (o padrão do fluxo é 1080×1350)")
    chamada = story_chamada(ciclo, post)
    erros += checar_encaixe.checar_varios(fs + ([chamada] if chamada and chamada.exists() else []))
    if erros:
        sys.exit("ERRO nos slides prontos:\n- " + "\n- ".join(erros))


def pagina_aprovacao(ciclo, post, digital):
    # Imagens embutidas: a página abre sozinha (celular, anexo, pré-visualização) sem depender da pasta slides/.
    if post.get("formato") == "reel":  # vídeo não cabe embutido: mostra a folha de quadros e aponta o arquivo
        b64 = base64.b64encode((ciclo / "previa.jpg").read_bytes()).decode()
        imgs = (f'<figure style="flex-basis:100%"><img src="data:image/jpeg;base64,{b64}" alt="Quadros do vídeo">'
                f'<figcaption>Quadros do vídeo (o primeiro é a capa). Assista ao arquivo '
                f'{html.escape(post.get("video", "video.mp4"))} nesta pasta antes de aprovar.</figcaption></figure>')
    else:
        imgs = "".join(f'<figure><img src="data:image/jpeg;base64,{base64.b64encode(p.read_bytes()).decode()}" alt="Slide {k}">'
                       f'<figcaption>{k}/{len(imagens(ciclo))}</figcaption></figure>'
                       for k, p in enumerate(imagens(ciclo), 1))
    pend = "".join(f"<li>{html.escape(x)}</li>" for x in post.get("pendencias", [])) or "<li>Nenhuma</li>"
    fontes = "".join(f"<li>{html.escape(x)}</li>" for x in post.get("fontes_fatos", []))
    legenda = html.escape(texto_final(post))
    quando = post.get("agendar_para") or "logo após a aprovação"
    pagina = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aprovação do post</title>
<style>
:root{{--azul:#1F4BA5;--ceu:#8CC8F2;--verde:#8EDC3A;--nevoa:#EAF4FC;--marinho:#0E2350;--fundo:#F6FAFE;--card:#fff;--texto:#0E2350}}
@media (prefers-color-scheme:dark){{:root{{--fundo:#0B1630;--card:#132449;--texto:#EAF4FC}}}}
body{{margin:0;background:var(--fundo);color:var(--texto);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px 60px}}
h1{{color:var(--azul);margin:0 0 4px;font-size:28px}} @media (prefers-color-scheme:dark){{h1{{color:var(--ceu)}}}}
.sub{{opacity:.75;margin:0 0 20px}}
.trilho{{display:flex;gap:14px;overflow-x:auto;padding-bottom:10px;scroll-snap-type:x mandatory}}
figure{{margin:0;flex:0 0 min(320px,80vw);scroll-snap-align:start}} img{{width:100%;border-radius:14px;box-shadow:0 6px 20px #0E235033;display:block}}
figcaption{{text-align:center;font-size:13px;opacity:.7;margin-top:6px}}
section{{background:var(--card);border-radius:16px;padding:18px 20px;margin-top:20px;box-shadow:0 2px 10px #0E235014}}
h2{{font-size:18px;margin:0 0 10px}} pre{{white-space:pre-wrap;font:inherit;margin:0}}
.aprovar{{border:3px solid var(--verde)}} code{{background:#8CC8F233;padding:2px 6px;border-radius:6px}}
</style></head><body><main>
<h1>{html.escape(post.get('pauta', post['ciclo']))}</h1>
<p class="sub">Ciclo <b>{html.escape(post['ciclo'])}</b> · conta {html.escape(post.get('conta', '?'))} · {html.escape(post.get('formato', ''))} · publicação: {html.escape(quando)} · gerado em {datetime.now():%d/%m/%Y %H:%M}</p>
<div class="trilho">{imgs}</div>
<section><h2>Legenda do post</h2><pre>{legenda}</pre></section>
<section><h2>Para decidir antes de aprovar</h2><ul>{pend}</ul></section>
<section><h2>De onde vieram os fatos</h2><ul>{fontes}</ul></section>
<section class="aprovar"><h2>Como aprovar</h2>
<p>Responda na conversa com o Claude: <code>aprovado {html.escape(post['ciclo'])}</code> — ou diga o que mudar.
Nada é publicado sem isso. A aprovação vale só para esta versão (impressão digital <code>{digital[:12]}</code>);
se qualquer imagem ou a legenda mudar, precisa aprovar de novo.</p></section>
</main></body></html>"""
    (ciclo / "aprovacao.html").write_text(pagina, encoding="utf-8")


def folha_previa(ciclo):
    """Todos os slides numa imagem só (previa.jpg) — para olhar rápido ou mandar no celular."""
    fs = imagens(ciclo)
    w, h, col = 360, 450, 4
    lin = (len(fs) + col - 1) // col
    folha = Image.new("RGB", (col * (w + 12) + 12, lin * (h + 12) + 12), "#D9E6F2")
    for i, f in enumerate(fs):
        folha.paste(Image.open(f).resize((w, h)), (12 + (i % col) * (w + 12), 12 + (i // col) * (h + 12)))
    folha.save(ciclo / "previa.jpg", quality=88)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ciclo = pasta_ciclo(sys.argv[1])
    post = ler_post(ciclo)
    erros = validar_post(post)
    if erros:
        print("ERRO no post.json:\n- " + "\n- ".join(erros))
        sys.exit(2)
    if (ciclo / "aprovacao.json").exists():
        (ciclo / "aprovacao.json").rename(ciclo / f"aprovacao-anterior-{datetime.now():%Y%m%d%H%M%S}.json")
        print("Aviso: havia uma aprovação anterior — ela foi arquivada; esta versão precisa de nova aprovação.")
    if post.get("origem") == "canva":
        conferir_slides_prontos(ciclo, post)
    else:
        renderizar(ciclo, post)
    digital = impressao_digital(ciclo, post)
    pagina_aprovacao(ciclo, post, digital)
    folha_previa(ciclo)
    print(f"OK: {len(imagens(ciclo))} slides em {ciclo / 'slides'}")
    print(f"Página de aprovação: {ciclo / 'aprovacao.html'}")
    print(f"Impressão digital: {digital[:12]}")


if __name__ == "__main__":
    main()
