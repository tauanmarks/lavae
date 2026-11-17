"""Publica um ciclo APROVADO no Instagram pela API oficial (Instagram API com login do Instagram).

    python automacao-instagram/publicar.py 2026-11-16-primeira-vez              # simulação (padrão)
    python automacao-instagram/publicar.py 2026-11-16-primeira-vez --de-verdade # publica

Trava de segurança:
  - sem aprovacao.json, ou se imagens/legenda mudaram depois da aprovação → recusa;
  - ciclo já publicado (publicacao.json com id) → recusa;
  - o token nunca é impresso nem gravado em relatório.

Configuração (variáveis de ambiente ou arquivo automacao-instagram/.env, que NÃO deve ser compartilhado):
  IG_USER_ID        id da conta profissional do Instagram
  IG_ACCESS_TOKEN   token com instagram_business_basic + instagram_business_content_publish
  IG_BASE_URL       endereço público da pasta ciclos/ (a API baixa a imagem por URL):
                    <IG_BASE_URL>/<ciclo>/slides/slide-01.jpg. No GitHub Actions é preenchido sozinho com o
                    endereço "raw" do repositório no commit publicado (exige repositório público).
  IG_API_VERSAO     opcional, padrão v23.0
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from comum import AUTO, impressao_digital, imagens, ler_post, pasta_ciclo, texto_final

API = "https://graph.instagram.com"


def carregar_config() -> dict:
    env = AUTO / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
    return {k: os.environ.get(k, "") for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "IG_BASE_URL")} | {
        "IG_API_VERSAO": os.environ.get("IG_API_VERSAO", "v23.0")}


def chamar(metodo: str, caminho: str, cfg: dict, campos: dict) -> dict:
    url = f"{API}/{cfg['IG_API_VERSAO']}/{caminho}"
    campos = dict(campos, access_token=cfg["IG_ACCESS_TOKEN"])
    dados = urllib.parse.urlencode(campos).encode()
    if metodo == "GET":
        req = urllib.request.Request(url + "?" + dados.decode())
    else:
        req = urllib.request.Request(url, data=dados, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="replace").replace(cfg["IG_ACCESS_TOKEN"], "***")
        raise SystemExit(f"ERRO da API ({e.code}) em {caminho}: {corpo[:800]}")


def url_publica_ok(url: str) -> str:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            tipo = r.headers.get("Content-Type", "")
            return "" if r.status == 200 and "jpeg" in tipo else f"{url} → {r.status} {tipo}"
    except Exception as e:  # noqa: BLE001
        return f"{url} → {e}"


def esperar_pronto(cid: str, cfg: dict, limite=300):
    t0 = time.time()
    while time.time() - t0 < limite:
        st = chamar("GET", cid, cfg, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"ERRO: contêiner {cid} ficou {st}")
        time.sleep(5)
    raise SystemExit(f"ERRO: contêiner {cid} não ficou pronto em {limite}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ciclo")
    ap.add_argument("--de-verdade", action="store_true", help="publica de fato (sem isso, só simula)")
    a = ap.parse_args()
    ciclo = pasta_ciclo(a.ciclo)
    post = ler_post(ciclo)
    imgs = imagens(ciclo)

    # 1. Travas
    aprov = ciclo / "aprovacao.json"
    if not aprov.exists():
        raise SystemExit("RECUSADO: ciclo sem aprovação. Mostre aprovacao.html e espere o 'aprovado'.")
    reg = json.loads(aprov.read_text(encoding="utf-8"))
    if reg.get("impressao_digital") != impressao_digital(ciclo, post):
        raise SystemExit("RECUSADO: imagens ou legenda mudaram depois da aprovação. Gere de novo e peça nova aprovação.")
    pub = ciclo / "publicacao.json"
    if pub.exists() and json.loads(pub.read_text(encoding="utf-8")).get("id"):
        raise SystemExit("RECUSADO: este ciclo já foi publicado (publicacao.json).")
    legenda = texto_final(post)
    carrossel = len(imgs) > 1

    cfg = carregar_config()
    base = cfg["IG_BASE_URL"].rstrip("/") or "https://<IG_BASE_URL>"
    urls = [f"{base}/{ciclo.name}/slides/{p.name}" for p in imgs]

    # 2. Plano de chamadas (o que a simulação mostra)
    passos = []
    if carrossel:
        passos += [f"POST /{{IG_USER_ID}}/media  image_url={u}  is_carousel_item=true" for u in urls]
        passos.append(f"POST /{{IG_USER_ID}}/media  media_type=CAROUSEL  children=<{len(urls)} ids>  caption=<{len(legenda)} caracteres>"
                      + ("  is_ai_generated=true" if post.get("rotulo_ia") else ""))
    else:
        passos.append(f"POST /{{IG_USER_ID}}/media  image_url={urls[0]}  caption=<{len(legenda)} caracteres>")
    passos += ["GET  /{container}?fields=status_code  (até FINISHED)", "POST /{IG_USER_ID}/media_publish  creation_id={container}",
               "GET  /{media_id}?fields=permalink"]

    if not a.de_verdade:
        faltando = [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "IG_BASE_URL") if not cfg[k]]
        print(f"SIMULAÇÃO — {ciclo.name}: aprovado por {reg['por']} em {reg['em']}, {len(imgs)} imagens, legenda {len(legenda)} caracteres")
        print("Chamadas que seriam feitas:\n  " + "\n  ".join(passos))
        print("Configuração faltando para publicar: " + (", ".join(faltando) if faltando else "nada"))
        return

    # 3. Publicação real
    faltando = [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "IG_BASE_URL") if not cfg[k]]
    if faltando:
        raise SystemExit("ERRO: falta configurar " + ", ".join(faltando) + " (veja o topo deste arquivo).")
    ruins = [x for x in (url_publica_ok(u) for u in urls) if x]
    if ruins:
        raise SystemExit("ERRO: imagens não estão acessíveis publicamente como JPEG:\n  " + "\n  ".join(ruins))
    uid = cfg["IG_USER_ID"]
    if carrossel:
        filhos = [chamar("POST", f"{uid}/media", cfg, {"image_url": u, "is_carousel_item": "true"})["id"] for u in urls]
        for f in filhos:
            esperar_pronto(f, cfg)
        campos = {"media_type": "CAROUSEL", "children": ",".join(filhos), "caption": legenda}
    else:
        campos = {"image_url": urls[0], "caption": legenda}
    if post.get("rotulo_ia"):
        campos["is_ai_generated"] = "true"
    cont = chamar("POST", f"{uid}/media", cfg, campos)["id"]
    esperar_pronto(cont, cfg)
    mid = chamar("POST", f"{uid}/media_publish", cfg, {"creation_id": cont})["id"]
    link = chamar("GET", mid, cfg, {"fields": "permalink"}).get("permalink", "")
    pub.write_text(json.dumps({"id": mid, "permalink": link, "em": datetime.now().isoformat(timespec="seconds"),
                               "impressao_digital": reg["impressao_digital"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PUBLICADO: {link or mid}")


if __name__ == "__main__":
    main()
