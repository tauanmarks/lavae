"""gerar_ficha.py — gera a ficha de marca revisável a partir de fichas-de-marca/marcas.json.

Uso:  python ferramentas/pipeline/gerar_ficha.py
Saídas:
  fichas-de-marca/ficha-de-marca.html          (todas as marcas, para revisar)
  ferramentas/remotion-projeto/src/marcas/marcas.json  (tema usado pelos componentes do Remotion)
"""
import html, json, shutil, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / "fichas-de-marca" / "marcas.json"
OUT = RAIZ / "fichas-de-marca" / "ficha-de-marca.html"
REMOTION = RAIZ / "ferramentas" / "remotion-projeto" / "src" / "marcas" / "marcas.json"

D = json.loads(SRC.read_text(encoding="utf-8"))
e = lambda s: html.escape(str(s))


def familias_google():
    fams = {}
    for m in D["marcas"]:
        for papel, f in m["fontes"].items():
            nome = f["familia"]
            fams.setdefault(nome, set())
            c = m["codigo"]["fontes"]
            peso = c.get(f"{papel}Peso", "400")
            ital = papel == "titulo" and c.get("tituloEstilo") == "italic"
            fams[nome].add((1 if ital else 0, int(peso)))
    partes = []
    for nome, pesos in sorted(fams.items()):
        pesos = sorted(pesos | {(0, 400)})
        if any(i for i, _ in pesos):
            spec = "ital,wght@" + ";".join(f"{i},{w}" for i, w in pesos)
        else:
            spec = "wght@" + ";".join(str(w) for _, w in pesos)
        partes.append("family=" + nome.replace(" ", "+") + ":" + spec)
    return "https://fonts.googleapis.com/css2?" + "&".join(partes) + "&display=swap"


def lum(hexc):
    h = hexc.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def tela(m):
    """Prévia 9:16 em CSS: fundo, cartão de título e legenda no estilo da marca."""
    c = m["codigo"]; L = c["legenda"]; F = m["fontes"]; cf = c["fontes"]
    a, b = c["fundoDemo"]
    tf = F["titulo"]["familia"]; lf = F["legenda"]["familia"]; af = F["apoio"]["familia"]
    t_ital = "italic" if cf.get("tituloEstilo") == "italic" else "normal"
    caixa = "uppercase" if L.get("caixaAlta") else ("lowercase" if L.get("minusculas") else "none")
    contorno = L.get("contorno", 0)
    stroke = f"-webkit-text-stroke:{contorno * 0.36:.1f}px {L['corContorno']};paint-order:stroke fill;" if contorno else f"text-shadow:0 2px 10px {L['corContorno']}99;"
    # frase de exemplo e destaque
    exemplos = {
        "palavra": (["NÃO", "ACREDITO"], "ACREDITO"),
        "frase": (["e", "foi", "ali", "que", "tudo", "mudou"], "mudou"),
        "bloco": (["olha", "como", "fica", "o", "resultado"], "resultado"),
    }
    palavras, kw = exemplos.get(L["modo"], exemplos["bloco"])
    spans = []
    for p in palavras:
        if p == kw:
            st = f"color:{L['corDestaque']};"
            if L.get("fundoDestaque"):
                st += f"background:{L['fundoDestaque']};padding:0 .18em;border-radius:.12em;-webkit-text-stroke:0;"
            if L.get("sublinhado"):
                st += f"text-decoration:underline;text-decoration-color:{L['sublinhado']};text-decoration-thickness:.12em;text-underline-offset:.12em;"
            if L.get("destaqueItalico"):
                st += f"font-family:'{tf}',serif;font-style:italic;"
            spans.append(f'<span class="kw" style="{st}">{e(p)}</span>')
        else:
            spans.append(f"<span>{e(p)}</span>")
    fs = L["tamanho"] * 0.36  # 1080 px → ~390 px de largura
    titulo_cor = m["cores"][1]["hex"] if lum(a) < 0.3 else m["cores"][4]["hex"]
    anim = {"pop": "cap-pop", "elastico": "cap-elastic", "subir": "cap-up", "fade": "cap-fade", "desfoque": "cap-blur"}.get(L["entrada"], "cap-up")
    zoom = c["zoom"]["punch"] if c["zoom"]["punch"] > 1.0 else c["zoom"]["lento"]
    zanim = "zoom-punch" if c["zoom"]["punch"] > 1.0 and c["zoom"]["duracaoPunch"] == 0 else "zoom-slow"
    return f"""
<div class="phone" aria-label="Prévia 9:16 da marca {e(m['nome'])}">
  <div class="phone-bg {zanim}" style="--a:{a};--b:{b};--z:{zoom}">
    <div class="ph-silhueta"></div>
  </div>
  <div class="ph-title" style="font-family:'{tf}';font-style:{t_ital};font-weight:{cf['tituloPeso']};color:{titulo_cor}">{e(m['nome'])}</div>
  <div class="ph-tag" style="font-family:'{af}';font-weight:{cf['apoioPeso']};background:{m['cores'][2]['hex']};color:{m['cores'][4]['hex'] if lum(m['cores'][2]['hex']) > 0.4 else '#fff'}">{e(m['contextos'][0])}</div>
  <div class="ph-cap {anim}" style="top:{L['y'] * 100:.0f}%;font-family:'{lf}';font-weight:{cf['legendaPeso']};font-size:{fs:.1f}px;color:{L['corTexto']};text-transform:{caixa};letter-spacing:{L.get('espacamento', 0) * 0.5}px;{stroke}">{' '.join(spans)}</div>
  <div class="ph-safe" title="Zonas seguras: topo 220 px, base 380 px, direita 160 px"></div>
</div>"""


def lista(itens):
    return "<ul>" + "".join(f"<li>{e(i)}</li>" for i in itens) + "</ul>"


def secao(m, idx):
    F = m["fontes"]; cf = m["codigo"]["fontes"]
    sw = "".join(
        f'<div class="sw"><div class="sw-c" style="background:{c["hex"]};color:{"#111" if lum(c["hex"]) > 0.45 else "#fff"}">{e(c["nome"])}</div>'
        f'<div class="sw-i"><code>{c["hex"]}</code><span>{e(c["uso"])}</span></div></div>' for c in m["cores"])
    fontes = ""
    for papel, rot in (("titulo", "Títulos"), ("legenda", "Legenda"), ("apoio", "Apoio")):
        f = F[papel]; ital = "italic" if papel == "titulo" and cf.get("tituloEstilo") == "italic" else "normal"
        peso = cf.get(f"{papel}Peso", "400")
        fontes += (f'<div class="font"><small>{rot}</small><div class="spec" style="font-family:\'{f["familia"]}\';font-weight:{peso};font-style:{ital}">'
                   f'Aa Bb 123 · ção</div><b>{e(f["familia"])} {e(f["peso"])}</b><span class="muted">{e(f["uso"])}</span></div>')
    Lg = m["legendas"]; Ct = m["cortes"]; R = m["ritmo"]; Mu = m["musica"]
    zooms = "".join(f"<li><b>{e(z['nome'])}</b> · {e(z['escala'])} · {e(z['duracao'])}<br><span class='muted'>{e(z['quando'])}</span></li>" for z in m["zooms"])
    anims = "".join(f"<li><b>{e(a['nome'])}</b><br><span class='muted'>{e(a['descricao'])}</span></li>" for a in m["animacoes"])
    sons = "".join(f"<li><b>{e(s['nome'])}</b> <span class='muted'>— {e(s['quando'])}</span></li>" for s in m["sons"])
    chips = "".join(f'<span class="chip">{e(c)}</span>' for c in m["contextos"])
    pers = " · ".join(e(p) for p in m["personalidade"])
    acc = m["cores"][1]["hex"]
    return f"""
<section class="marca" id="{m['id']}" style="--acc:{acc}">
  <div class="m-head">
    <div class="m-intro">
      <span class="num">Marca {idx:02d}</span>
      <h2 style="font-family:'{F['titulo']['familia']}';font-weight:{cf['tituloPeso']};font-style:{'italic' if cf.get('tituloEstilo') == 'italic' else 'normal'}">{e(m['nome'])}</h2>
      <p class="sig">“{e(m['assinatura'])}”</p>
      <div class="chips">{chips}</div>
      <p class="muted">Personalidade: {pers}</p>
      <label class="aprov"><input type="checkbox" data-id="{m['id']}"> Aprovada</label>
      <textarea class="obs" data-id="{m['id']}" placeholder="Anotações de revisão desta marca (ficam salvas neste navegador)"></textarea>
    </div>
    {tela(m)}
  </div>

  <h3>Cores</h3><div class="palette">{sw}</div>
  <h3>Fontes</h3><div class="fonts">{fontes}</div>

  <div class="grid">
    <div class="card"><h4>Legendas</h4><p>{e(Lg['estilo'])}</p>
      <dl><dt>Palavras por bloco</dt><dd>{e(Lg['palavras_por_bloco'])}</dd><dt>Posição</dt><dd>{e(Lg['posicao'])}</dd>
      <dt>Destaque</dt><dd>{e(Lg['destaque'])}</dd><dt>Entrada</dt><dd>{e(Lg['entrada'])}</dd></dl></div>
    <div class="card"><h4>Cortes</h4><p><b>Silêncio máximo:</b> {str(Ct['silencio_max_s']).replace('.', ',')} s</p>{lista(Ct['regras'])}</div>
    <div class="card"><h4>Zooms</h4><ul>{zooms}</ul></div>
    <div class="card"><h4>Ritmo</h4><dl><dt>Plano médio</dt><dd>{e(R['plano_medio_s'])} s</dd><dt>BPM de referência</dt><dd>{e(R['bpm'])}</dd></dl><p class="muted">{e(R['notas'])}</p></div>
    <div class="card"><h4>Animações</h4><ul>{anims}</ul></div>
    <div class="card"><h4>Transições</h4>{lista(m['transicoes'])}</div>
    <div class="card"><h4>Música</h4><dl><dt>Gênero</dt><dd>{e(Mu['genero'])}</dd><dt>BPM</dt><dd>{e(Mu['bpm'])}</dd><dt>Clima</dt><dd>{e(Mu['clima'])}</dd>
      <dt>Sob a fala</dt><dd>{Mu['volume_sob_fala_db']} dB</dd></dl><p class="muted">{e(Mu['regras'])}</p></div>
    <div class="card"><h4>Sons</h4><ul>{sons}</ul></div>
    <div class="card"><h4>Cor da imagem</h4><p>{e(m['cor_imagem'])}</p></div>
    <div class="card extra"><h4>Sugestões que agregam</h4>{lista(m['extras'])}</div>
  </div>
</section>"""


def tabela_escolha():
    linhas = "".join(
        f"<tr><td><a href='#{m['id']}'>{e(m['nome'])}</a></td><td>{e(', '.join(m['contextos']))}</td><td>{e(m['ritmo']['plano_medio_s'])} s</td><td>{e(m['musica']['genero'])}</td></tr>"
        for m in D["marcas"])
    return f"<div class='tbl'><table><thead><tr><th>Marca</th><th>Quando usar</th><th>Plano médio</th><th>Música</th></tr></thead><tbody>{linhas}</tbody></table></div>"


regras = "".join(f"<div class='card'><h4>{e(k.replace('_', ' ').capitalize())}</h4><p>{e(v)}</p></div>" for k, v in D["regras_gerais"].items())
nav = "".join(f"<a href='#{m['id']}' style='--acc:{m['cores'][1]['hex']}'>{e(m['nome'])}</a>" for m in D["marcas"])
corpo = "".join(secao(m, i + 1) for i, m in enumerate(D["marcas"]))

page = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fichas de Marca</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{familias_google()}" rel="stylesheet">
<style>
:root {{ --bg:#F4F2EE; --surface:#FFFFFF; --fg:#17161A; --muted:#6B6772; --line:#E3DFD8; --chip:#ECE8E1; color-scheme:light; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#121115; --surface:#1C1B21; --fg:#F2EFEA; --muted:#A6A1AD; --line:#2E2C35; --chip:#2A2830; color-scheme:dark; }} }}
:root[data-theme="dark"] {{ --bg:#121115; --surface:#1C1B21; --fg:#F2EFEA; --muted:#A6A1AD; --line:#2E2C35; --chip:#2A2830; color-scheme:dark; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.6 "Inter","Segoe UI",system-ui,sans-serif; padding:0 max(16px,env(safe-area-inset-left)); }}
.wrap {{ max-width:1100px; margin:0 auto; padding:40px 0 100px; display:grid; gap:56px; }}
h1 {{ font:800 clamp(38px,6vw,68px)/1 "Space Grotesk",system-ui,sans-serif; letter-spacing:-.035em; margin:0; }}
h2 {{ font-size:clamp(40px,6vw,64px); line-height:1; margin:4px 0 6px; letter-spacing:-.02em; }}
h3 {{ font:700 13px/1 "Space Grotesk",sans-serif; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); margin:28px 0 12px; }}
h4 {{ margin:0 0 8px; font:700 17px/1.2 "Space Grotesk",sans-serif; }}
p {{ margin:0 0 8px; }} ul {{ margin:0; padding-left:18px; }} li {{ margin:0 0 6px; }}
.muted {{ color:var(--muted); }}
.lead {{ font-size:17px; color:var(--muted); max-width:70ch; }}
nav {{ position:sticky; top:0; z-index:5; background:color-mix(in srgb,var(--bg) 88%,transparent); backdrop-filter:blur(8px); display:flex; gap:8px; overflow-x:auto; padding:10px 0; border-bottom:1px solid var(--line); }}
nav a {{ flex:none; text-decoration:none; color:var(--fg); font-weight:700; font-size:13px; padding:6px 12px; border-radius:999px; background:var(--chip); border-left:6px solid var(--acc); }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:18px; min-width:0; }}
.regras {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px; }}
.tbl {{ overflow-x:auto; border:1px solid var(--line); border-radius:14px; background:var(--surface); }}
table {{ border-collapse:collapse; width:100%; min-width:640px; font-size:14px; }}
th,td {{ text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}
td a {{ color:var(--fg); font-weight:800; }}
.marca {{ border-top:6px solid var(--acc); padding-top:28px; scroll-margin-top:60px; }}
.m-head {{ display:grid; grid-template-columns:1fr auto; gap:32px; align-items:start; }}
@media (max-width:760px) {{ .m-head {{ grid-template-columns:1fr; }} .phone {{ justify-self:center; }} }}
.num {{ font:700 12px/1 "Space Grotesk",sans-serif; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }}
.sig {{ font-size:20px; font-style:italic; color:var(--muted); }}
.chips {{ display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 12px; }}
.chip {{ background:var(--chip); border-radius:999px; padding:3px 10px; font-size:13px; font-weight:600; }}
.aprov {{ display:inline-flex; gap:8px; align-items:center; font-weight:700; margin:8px 0; cursor:pointer; }}
.aprov input {{ width:18px; height:18px; accent-color:var(--acc); }}
.obs {{ width:100%; min-height:72px; resize:vertical; border:1px solid var(--line); border-radius:10px; padding:10px; background:var(--surface); color:var(--fg); font:inherit; }}
.palette {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }}
.sw {{ border:1px solid var(--line); border-radius:12px; overflow:hidden; background:var(--surface); }}
.sw-c {{ height:76px; display:flex; align-items:flex-end; padding:8px 10px; font-weight:800; font-size:15px; }}
.sw-i {{ padding:8px 10px 10px; display:grid; gap:2px; font-size:13px; line-height:1.4; }}
.sw-i code {{ color:var(--muted); font-size:12px; }}
.fonts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:10px; }}
.font {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:14px; display:grid; gap:4px; }}
.font small {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.1em; font-weight:700; }}
.font .spec {{ font-size:34px; line-height:1.1; min-height:44px; overflow-wrap:anywhere; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:12px; margin-top:28px; }}
dl {{ display:grid; grid-template-columns:auto 1fr; gap:4px 12px; margin:0; font-size:14px; }}
dt {{ color:var(--muted); }} dd {{ margin:0; }}
.extra {{ border:2px dashed var(--acc); }}
/* prévia 9:16 */
.phone {{ position:relative; width:270px; aspect-ratio:9/16; border-radius:26px; overflow:hidden; box-shadow:0 18px 40px -18px #0008; border:6px solid #111; background:#000; }}
.phone-bg {{ position:absolute; inset:0; background:radial-gradient(120% 80% at 30% 20%,var(--b),var(--a)); }}
.ph-silhueta {{ position:absolute; left:50%; bottom:-6%; width:62%; aspect-ratio:1/1.25; transform:translateX(-50%); background:radial-gradient(circle at 50% 22%,#0003 0 22%,transparent 23%),radial-gradient(ellipse at 50% 100%,#0003 0 55%,transparent 56%); }}
.zoom-punch {{ animation:zp 3s infinite steps(1); }}
@keyframes zp {{ 0%,55% {{ transform:scale(1); }} 56%,100% {{ transform:scale(var(--z)); }} }}
.zoom-slow {{ animation:zs 6s ease-in-out infinite alternate; }}
@keyframes zs {{ from {{ transform:scale(1); }} to {{ transform:scale(var(--z)); }} }}
.ph-title {{ position:absolute; top:12%; left:8%; right:8%; font-size:36px; line-height:.95; letter-spacing:-.01em; }}
.ph-tag {{ position:absolute; top:calc(12% + 52px); left:8%; font-size:12px; padding:3px 8px; border-radius:6px; }}
.ph-cap {{ position:absolute; left:6%; right:12%; text-align:center; line-height:1.15; transform-origin:center; }}
.ph-cap .kw {{ display:inline-block; }}
.ph-safe {{ position:absolute; inset:calc(220/1920*100%) calc(160/1080*100%) calc(380/1920*100%) 0; border:1px dashed #fff5; border-left:0; pointer-events:none; }}
.cap-pop {{ animation:cp 3s infinite; }} @keyframes cp {{ 0% {{ opacity:0; transform:scale(.9); }} 4%,90% {{ opacity:1; transform:scale(1); }} 100% {{ opacity:0; }} }}
.cap-elastic {{ animation:ce 1.5s infinite; }} @keyframes ce {{ 0% {{ transform:scale(.8); opacity:0; }} 8% {{ transform:scale(1.12); opacity:1; }} 14%,92% {{ transform:scale(1); opacity:1; }} 100% {{ opacity:0; }} }}
.cap-up {{ animation:cu 3s infinite; }} @keyframes cu {{ 0% {{ opacity:0; transform:translateY(8px); }} 5%,90% {{ opacity:1; transform:none; }} 100% {{ opacity:0; }} }}
.cap-fade {{ animation:cf 3s infinite; }} @keyframes cf {{ 0% {{ opacity:0; }} 8%,88% {{ opacity:1; }} 100% {{ opacity:0; }} }}
.cap-blur {{ animation:cb 4s infinite; }} @keyframes cb {{ 0% {{ opacity:0; filter:blur(6px); }} 10%,88% {{ opacity:1; filter:none; }} 100% {{ opacity:0; }} }}
@media (prefers-reduced-motion: reduce) {{ .phone-bg,.ph-cap {{ animation:none !important; }} }}
footer {{ color:var(--muted); font-size:13px; border-top:1px solid var(--line); padding-top:16px; }}
</style></head>
<body><div class="wrap">
<header style="display:grid;gap:14px">
  <span class="num">Editor Variado · versão {e(D['versao'])} · {e(D['data'])}</span>
  <h1>Fichas de Marca</h1>
  <p class="lead">{len(D["marcas"])} marcas de edição, uma para cada contexto de vídeo. Cada uma tem fontes, cores, legendas, cortes, zooms, ritmo, animações, música e sons próprios. Marque as aprovadas e anote ajustes: eu atualizo o <code>marcas.json</code> e esta ficha.</p>
</header>
<nav>{nav}</nav>
<section style="display:grid;gap:14px"><h3 style="margin:0">Qual marca usar</h3>{tabela_escolha()}
<p class="muted">Na análise do vídeo bruto eu sugiro a marca pelos sinais da fala e da imagem; a escolha final é sua, no storyboard. Um vídeo pode misturar: marca principal + um recurso de outra (ex.: Diário Solto com o veredito da Prova Real).</p></section>
<section style="display:grid;gap:14px"><h3 style="margin:0">Regras de todas as marcas</h3><div class="regras">{regras}</div></section>
{corpo}
<footer>Gerado por <code>ferramentas/pipeline/gerar_ficha.py</code> a partir de <code>fichas-de-marca/marcas.json</code>. As prévias 9:16 são aproximações em CSS; a linha tracejada marca a zona segura.</footer>
</div>
<script>
// Aprovação e anotações ficam só neste navegador (conveniência de revisão).
const K = "fichas-marca-revisao";
let st = {{}}; try {{ st = JSON.parse(localStorage.getItem(K) || "{{}}"); }} catch (_) {{}}
const save = () => {{ try {{ localStorage.setItem(K, JSON.stringify(st)); }} catch (_) {{}} }};
document.querySelectorAll(".aprov input").forEach(i => {{ i.checked = !!(st[i.dataset.id] || {{}}).ok;
  i.onchange = () => {{ st[i.dataset.id] = {{...(st[i.dataset.id] || {{}}), ok: i.checked}}; save(); }}; }});
document.querySelectorAll(".obs").forEach(t => {{ t.value = (st[t.dataset.id] || {{}}).obs || "";
  t.oninput = () => {{ st[t.dataset.id] = {{...(st[t.dataset.id] || {{}}), obs: t.value}}; save(); }}; }});
</script>
</body></html>"""

OUT.write_text(page, encoding="utf-8")
REMOTION.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(SRC, REMOTION)
print(f"ok: {OUT.relative_to(RAIZ)}  ({len(D['marcas'])} marcas)")
print(f"ok: {REMOTION.relative_to(RAIZ)}")
