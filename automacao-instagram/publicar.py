"""Publica um ciclo APROVADO no Instagram pela API oficial (Instagram API com login do Instagram).

    python automacao-instagram/publicar.py 2026-11-16-primeira-vez              # simulação (padrão)
    python automacao-instagram/publicar.py 2026-11-16-primeira-vez --de-verdade # publica

Trava de segurança:
  - sem aprovacao.json, ou se imagens/legenda mudaram depois da aprovação → recusa;
  - ciclo já publicado (publicacao.json com id) → recusa (se só faltou o story de chamada, publica só ele);
  - o token nunca é impresso nem gravado em relatório.

Configuração (variáveis de ambiente ou arquivo automacao-instagram/.env, que NÃO deve ser compartilhado):
  IG_USER_ID        id da conta profissional do Instagram
  IG_ACCESS_TOKEN   token com instagram_business_basic + instagram_business_content_publish
  IG_BASE_URL       endereço público da pasta ciclos/ (a API baixa a imagem por URL):
                    <IG_BASE_URL>/<ciclo>/slides/slide-01.jpg. No GitHub Actions é preenchido sozinho com o
                    endereço "raw" do repositório no commit publicado (exige repositório público).
  IG_API_VERSAO     opcional, padrão v23.0
  IG_API_HOST       opcional: "instagram" (padrão, login do Instagram, graph.instagram.com) ou
                    "facebook" (login do Facebook com Página ligada ao Instagram, graph.facebook.com;
                    token com instagram_basic + instagram_content_publish + pages_show_list + pages_read_engagement)
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from comum import AUTO, eh_reel, impressao_digital, imagens, ler_post, midias, pasta_ciclo, story_chamada, texto_final

HOSTS = {"instagram": "https://graph.instagram.com", "facebook": "https://graph.facebook.com"}


def carregar_config() -> dict:
    env = AUTO / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
    host = (os.environ.get("IG_API_HOST") or "instagram").strip().lower()
    if host not in HOSTS:
        raise SystemExit(f"ERRO: IG_API_HOST deve ser 'instagram' ou 'facebook' (veio '{host}')")
    # "or": no Actions a variável não definida chega vazia
    return {k: os.environ.get(k, "").strip() for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "IG_BASE_URL")} | {
        "IG_API_VERSAO": os.environ.get("IG_API_VERSAO") or "v23.0", "IG_API_HOST": host, "API": HOSTS[host]}


def chamar(metodo: str, caminho: str, cfg: dict, campos: dict) -> dict:
    url = f"{cfg['API']}/{cfg['IG_API_VERSAO']}/{caminho}"
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


def esperar_pronto(cid: str, cfg: dict, limite=300, intervalo=5):
    t0 = time.time()
    while time.time() - t0 < limite:
        r = chamar("GET", cid, cfg, {"fields": "status_code,status"})
        st = r.get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"ERRO: contêiner {cid} ficou {st}: {r.get('status', '')}")
        time.sleep(intervalo)
    raise SystemExit(f"ERRO: contêiner {cid} não ficou pronto em {limite}s")


def enviar_video(uri: str, arq, cfg: dict) -> None:
    """Envio direto (resumable upload) do arquivo de vídeo para o contêiner criado."""
    dados = arq.read_bytes()
    # Igual ao exemplo oficial (curl --data-binary): só Authorization, offset e file_size.
    req = urllib.request.Request(uri, data=dados, method="POST", headers={
        "Authorization": f"OAuth {cfg['IG_ACCESS_TOKEN']}", "offset": "0", "file_size": str(len(dados))})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            resp = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="replace").replace(cfg["IG_ACCESS_TOKEN"], "***")
        raise SystemExit(f"ERRO no envio do vídeo ({e.code}): {corpo[:800]}")
    if not resp.get("success", True):
        raise SystemExit(f"ERRO no envio do vídeo: {resp}")


def video_publico_ok(url: str, tamanho: int) -> str:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
            n = int(r.headers.get("Content-Length") or 0)
            return "" if r.status == 200 and n == tamanho else f"{url} → {r.status}, {n} bytes (esperado {tamanho})"
    except Exception as e:  # noqa: BLE001
        return f"{url} → {e}"


def publicar_reel(ciclo, post, reg, pub, de_verdade):
    """Reels no feed. Com endereço público (IG_BASE_URL, preenchido sozinho no GitHub Actions) a Meta baixa o vídeo
    pelo link (video_url). Sem ele, ou com IG_REEL_ENVIO=resumable, envia o arquivo direto (resumable upload, que a
    Meta só libera para apps com 'Login do Facebook para Empresas')."""
    cfg = carregar_config()
    video = midias(ciclo, post)[0]
    legenda = texto_final(post)
    base = cfg["IG_BASE_URL"].rstrip("/")
    por_link = bool(base) and os.environ.get("IG_REEL_ENVIO", "").lower() != "resumable"
    url_video = f"{base}/{ciclo.name}/{video.name}" if base else ""
    campos = {"media_type": "REELS", "caption": legenda, "share_to_feed": "true"}
    if por_link:
        campos["video_url"] = url_video
    else:
        campos["upload_type"] = "resumable"
    if post.get("capa_ms") is not None:
        campos["thumb_offset"] = str(int(post["capa_ms"]))
    if post.get("rotulo_ia"):
        campos["is_ai_generated"] = "true"
    passos = [f"POST /{{IG_USER_ID}}/media  " + "  ".join(f"{k}={v if k != 'caption' else f'<{len(legenda)} caracteres>'}"
                                                         for k, v in campos.items()),
              (f"(a Meta baixa {video.name}, {video.stat().st_size / 1e6:.1f} MB, pelo link)" if por_link else
               f"POST <uri de envio>  ({video.name}, {video.stat().st_size / 1e6:.1f} MB, cabeçalhos offset/file_size)"),
              "GET  /{container}?fields=status_code,status  (até FINISHED; vídeo leva alguns minutos)",
              "POST /{IG_USER_ID}/media_publish  creation_id={container}", "GET  /{media_id}?fields=permalink"]
    faltando = [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN") if not cfg[k]]
    if not de_verdade:
        print(f"SIMULAÇÃO — {ciclo.name}: reel aprovado por {reg['por']} em {reg['em']}, "
              f"{video.name} {video.stat().st_size / 1e6:.1f} MB, legenda {len(legenda)} caracteres")
        print("Chamadas que seriam feitas:\n  " + "\n  ".join(passos))
        print("Configuração faltando para publicar: " + (", ".join(faltando) if faltando else "nada"))
        return
    if faltando:
        raise SystemExit("ERRO: falta configurar " + ", ".join(faltando) + " (veja o topo deste arquivo).")
    uid = cfg["IG_USER_ID"]
    if por_link:
        ruim = video_publico_ok(url_video, video.stat().st_size)
        if ruim:
            raise SystemExit(f"ERRO: o vídeo não está acessível pelo link público: {ruim}")
        cont = chamar("POST", f"{uid}/media", cfg, campos)["id"]
        print(f"  contêiner {cont} criado; a Meta está baixando o vídeo pelo link…", flush=True)
    else:
        r = chamar("POST", f"{uid}/media", cfg, campos)
        cont, uri = r["id"], r.get("uri")
        if not uri:
            raise SystemExit(f"ERRO: a API não devolveu o endereço de envio: {r}")
        print(f"  contêiner {cont} criado; enviando {video.stat().st_size / 1e6:.1f} MB…", flush=True)
        enviar_video(uri, video, cfg)
        print("  vídeo enviado; aguardando o Instagram processar…", flush=True)
    esperar_pronto(cont, cfg, limite=900, intervalo=15)
    mid = chamar("POST", f"{uid}/media_publish", cfg, {"creation_id": cont})["id"]
    link = chamar("GET", mid, cfg, {"fields": "permalink"}).get("permalink", "")
    pub.write_text(json.dumps({"id": mid, "permalink": link, "formato": "reel",
                               "em": datetime.now().isoformat(timespec="seconds"),
                               "impressao_digital": reg["impressao_digital"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PUBLICADO: {link or mid}")


def publicar_stories(ciclo, post, reg, pub, imgs, de_verdade):
    """Sequência de stories (imagens 9:16), publicadas uma a uma na ordem dos arquivos.
    Se cair no meio, o publicacao.json guarda os ids já publicados e uma nova execução continua de onde parou."""
    cfg = carregar_config()
    base = cfg["IG_BASE_URL"].rstrip("/") or "https://<IG_BASE_URL>"
    urls = [f"{base}/{ciclo.name}/slides/{p.name}" for p in imgs]
    feitos = json.loads(pub.read_text(encoding="utf-8")).get("ids", []) if pub.exists() else []
    faltando = [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "IG_BASE_URL") if not cfg[k]]
    if not de_verdade:
        print(f"SIMULAÇÃO — {ciclo.name}: sequência de {len(urls)} stories, aprovada por {reg['por']} em {reg['em']}"
              + (f" ({len(feitos)} já publicados)" if feitos else ""))
        for u in urls[len(feitos):]:
            print(f"  POST /{{IG_USER_ID}}/media  media_type=STORIES  image_url={u}  →  media_publish")
        print("Configuração faltando para publicar: " + (", ".join(faltando) if faltando else "nada"))
        return
    if faltando:
        raise SystemExit("ERRO: falta configurar " + ", ".join(faltando))
    ruins = [x for x in (url_publica_ok(u) for u in urls[len(feitos):]) if x]
    if ruins:
        raise SystemExit("ERRO: imagens não estão acessíveis publicamente como JPEG:\n  " + "\n  ".join(ruins))
    uid = cfg["IG_USER_ID"]
    for i, u in enumerate(urls[len(feitos):], len(feitos) + 1):
        cont = chamar("POST", f"{uid}/media", cfg, {"media_type": "STORIES", "image_url": u})["id"]
        esperar_pronto(cont, cfg, limite=180)
        feitos.append(chamar("POST", f"{uid}/media_publish", cfg, {"creation_id": cont})["id"])
        pub.write_text(json.dumps({"ids": feitos, "formato": "stories", "total": len(urls),
                                   "impressao_digital": reg["impressao_digital"]}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  story {i}/{len(urls)} publicado ({feitos[-1]})", flush=True)
        time.sleep(3)  # mantém a ordem da sequência
    pub.write_text(json.dumps({"id": feitos[-1], "ids": feitos, "formato": "stories", "total": len(urls),
                               "em": datetime.now().isoformat(timespec="seconds"),
                               "impressao_digital": reg["impressao_digital"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PUBLICADO: sequência de {len(feitos)} stories")


def publicar_chamada(ciclo, post, pub, de_verdade):
    """Story 9:16 ("story_chamada") logo depois do post do feed, convidando a ver o post.
    A API não põe figurinha de link: o story mostra o assunto e chama para o perfil."""
    cfg = carregar_config()
    base = cfg["IG_BASE_URL"].rstrip("/") or "https://<IG_BASE_URL>"
    url = f"{base}/{ciclo.name}/{post['story_chamada']}"
    if not de_verdade:
        print(f"  POST /{{IG_USER_ID}}/media  media_type=STORIES  image_url={url}  →  media_publish  (story de chamada)")
        return
    reg = json.loads(pub.read_text(encoding="utf-8"))
    ruim = url_publica_ok(url)
    if ruim:
        raise SystemExit(f"ERRO: story de chamada não acessível como JPEG: {ruim}")
    uid = cfg["IG_USER_ID"]
    cont = chamar("POST", f"{uid}/media", cfg, {"media_type": "STORIES", "image_url": url})["id"]
    esperar_pronto(cont, cfg, limite=180)
    reg["story_id"] = chamar("POST", f"{uid}/media_publish", cfg, {"creation_id": cont})["id"]
    reg["story_em"] = datetime.now().isoformat(timespec="seconds")
    pub.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PUBLICADO: story de chamada ({reg['story_id']})")


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
        raise SystemExit("RECUSADO: mídia ou legenda mudaram depois da aprovação. Gere de novo e peça nova aprovação.")
    pub = ciclo / "publicacao.json"
    chamada = story_chamada(ciclo, post)
    if chamada and not chamada.exists():
        raise SystemExit(f"ERRO: story de chamada {post['story_chamada']} não encontrado.")
    if pub.exists() and json.loads(pub.read_text(encoding="utf-8")).get("id"):
        if chamada and not json.loads(pub.read_text(encoding="utf-8")).get("story_id"):
            print("Post do feed já publicado; falta só o story de chamada.")
            return publicar_chamada(ciclo, post, pub, a.de_verdade)
        raise SystemExit("RECUSADO: este ciclo já foi publicado (publicacao.json).")
    if eh_reel(post):
        return publicar_reel(ciclo, post, reg, pub, a.de_verdade)
    if post.get("formato") == "stories":
        return publicar_stories(ciclo, post, reg, pub, imgs, a.de_verdade)
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
        if chamada:
            publicar_chamada(ciclo, post, pub, False)
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
    if chamada:
        time.sleep(30)  # o post aparece no perfil antes de o story chamar para ele
        publicar_chamada(ciclo, post, pub, True)


if __name__ == "__main__":
    main()
