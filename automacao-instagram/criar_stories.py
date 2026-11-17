"""Prepara as imagens do story diário a partir da exportação do Canva (marca Espuma, sem fotos por enquanto).

    python automacao-instagram/criar_stories.py --de-pasta PASTA   # importa 01.jpg…28.jpg exportados do Canva
    python automacao-instagram/criar_stories.py                    # só refaz prévia e página de revisão

A arte é feita no Canva (design em stories/modelo.json → "canva"): uma página por story, na ordem
segunda-1..4, terça-1..4 … domingo-4. Exporte como JPG 1080×1920 e importe aqui.
Saída: stories/imagens/<dia>-<n>.jpg, stories/previa.jpg (colunas = dias, linhas = semanas do rodízio) e
stories/aprovacao.html (com o calendário). Imagem que mudou perde a aprovação. Não publica nada.
"""
import base64
import html
import json
import argparse
import sys
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from stories_comum import APROVACAO, IMAGENS, STORIES, digital, hoje, ler_json, ler_modelo, lista_stories, story_do_dia


def importar(pasta, stories):
    fs = sorted(Path(pasta).glob("*.jpg"))
    if len(fs) != len(stories):
        sys.exit(f"ERRO: {len(fs)} JPG em {pasta}, esperava {len(stories)} (uma página do Canva por story)")
    IMAGENS.mkdir(exist_ok=True)
    ids = {s["id"] for s in stories}
    for velho in IMAGENS.glob("*.jpg"):
        if velho.stem not in ids:
            velho.unlink()
    for s, f in zip(stories, fs):
        im = Image.open(f)
        if im.format != "JPEG" or im.size != (1080, 1920):
            sys.exit(f"ERRO: {f.name} é {im.format} {im.size}; exporte do Canva como JPG 1080×1920")
        destino = IMAGENS / f"{s['id']}.jpg"
        novo = f.read_bytes()
        if not destino.exists() or destino.read_bytes() != novo:  # imagem igual mantém a aprovação
            destino.write_bytes(novo)


def conferir(stories):
    erros = []
    for s in stories:
        f = IMAGENS / f"{s['id']}.jpg"
        if not f.exists():
            erros.append(f"falta {f.name}")
            continue
        im = Image.open(f)
        if im.format != "JPEG" or im.size != (1080, 1920):
            erros.append(f"{f.name}: {im.format} {im.size} (precisa JPEG 1080×1920)")
        if f.stat().st_size > 8 * 1024 * 1024:
            erros.append(f"{f.name}: maior que 8 MB (limite da API)")
    if erros:
        sys.exit("ERRO nas imagens:\n- " + "\n- ".join(erros))


def fonte(tam):
    for nome in ("DejaVuSans-Bold.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
        try:
            return ImageFont.truetype(nome, tam)
        except OSError:
            pass
    return ImageFont.load_default()


def folha(modelo):
    dias = modelo["dias"]
    linhas = max(len(d["frases"]) for d in dias)
    w, h, pad, cab = 270, 480, 12, 40
    img = Image.new("RGB", (len(dias) * (w + pad) + pad, cab + linhas * (h + pad) + pad), "#D9E6F2")
    d = ImageDraw.Draw(img)
    for c, dia in enumerate(dias):
        x = pad + c * (w + pad)
        d.text((x + 4, 10), f"{dia['nome']} · R$ {dia['preco']}", fill="#0E2350", font=fonte(19))
        for k in range(len(dia["frases"])):
            img.paste(Image.open(IMAGENS / f"{dia['id']}-{k + 1}.jpg").resize((w, h)), (x, cab + k * (h + pad)))
    img.save(STORIES / "previa.jpg", quality=88)


def miniatura(arq) -> str:
    b = BytesIO()
    Image.open(arq).resize((540, 960)).save(b, "JPEG", quality=80)
    return base64.b64encode(b.getvalue()).decode()


def pagina(modelo, stories):
    aprov = ler_json(APROVACAO, {}).get("imagens", {})
    cal = []
    d0 = hoje()
    for n in range(28):
        dia = d0 + timedelta(days=n)
        sid = story_do_dia(modelo, dia)
        pulado = dia.isoformat() in modelo.get("pular", [])
        cal.append(f"<tr><td>{dia:%d/%m} {['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'][dia.weekday()]}</td>"
                   f"<td>{'— pulado —' if pulado else html.escape(sid)}</td></tr>")
    cards = []
    for s in stories:
        arq = IMAGENS / f"{s['id']}.jpg"
        ok = aprov.get(s["id"]) == digital(arq)
        cards.append(f'<figure><img src="data:image/jpeg;base64,{miniatura(arq)}" alt="{html.escape(s["id"])}">'
                     f'<figcaption><b>{html.escape(s["id"])}</b> · {"✓ aprovado" if ok else "aguardando aprovação"}</figcaption></figure>')
    pend = "".join(f"<li>{html.escape(x)}</li>" for x in modelo.get("pendencias", [])) or "<li>Nenhuma</li>"
    pagina = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stories diários</title><style>
:root{{--azul:#1F4BA5;--ceu:#8CC8F2;--verde:#8EDC3A;--fundo:#F6FAFE;--card:#fff;--texto:#0E2350}}
@media (prefers-color-scheme:dark){{:root{{--fundo:#0B1630;--card:#132449;--texto:#EAF4FC}}}}
body{{margin:0;background:var(--fundo);color:var(--texto);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1200px;margin:0 auto;padding:24px 16px 60px}} h1{{color:var(--azul);margin:0}}
.grade{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}}
figure{{margin:0}} img{{width:100%;border-radius:12px;display:block;box-shadow:0 4px 14px #0E235033}}
figcaption{{font-size:13px;margin-top:4px}} section{{background:var(--card);border-radius:16px;padding:16px 20px;margin-top:20px}}
table{{border-collapse:collapse}} td{{padding:2px 14px 2px 0}}
</style></head><body><main>
<h1>Stories diários — {len(stories)} imagens</h1>
<p>Sai um por dia às {html.escape(modelo['hora'])} (horário de São Luís). A frase de cada dia da semana troca a cada semana.</p>
<div class="grade">{''.join(cards)}</div>
<section><h2>Próximos 28 dias</h2><table>{''.join(cal)}</table></section>
<section><h2>Para decidir</h2><ul>{pend}</ul></section>
</main></body></html>"""
    (STORIES / "aprovacao.html").write_text(pagina, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--de-pasta", help="pasta com os JPG exportados do Canva (01.jpg…28.jpg, na ordem das páginas)")
    a = ap.parse_args()
    modelo = ler_modelo()
    stories = lista_stories(modelo)
    if a.de_pasta:
        importar(a.de_pasta, stories)
    conferir(stories)
    folha(modelo)
    pagina(modelo, stories)
    aprov = ler_json(APROVACAO, {}).get("imagens", {})
    faltam = [s["id"] for s in stories if aprov.get(s["id"]) != digital(IMAGENS / f"{s['id']}.jpg")]
    print(f"OK: {len(stories)} stories em {IMAGENS}")
    print(f"Prévia: {STORIES / 'previa.jpg'} · revisão: {STORIES / 'aprovacao.html'}")
    print(f"Sem aprovação: {len(faltam)}" + (f" ({', '.join(faltam[:6])}{'…' if len(faltam) > 6 else ''})" if faltam else ""))


if __name__ == "__main__":
    main()
