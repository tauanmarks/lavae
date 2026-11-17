"""Publica o story do dia (imagem aprovada do rodízio) no Instagram.

    python automacao-instagram/publicar_story.py                      # simulação de hoje
    python automacao-instagram/publicar_story.py --data 2026-11-18    # simulação de outro dia
    python automacao-instagram/publicar_story.py --esperar --de-verdade   # o que o GitHub Actions roda às 8h40

Travas:
  - imagem sem aprovação ou alterada depois de aprovada → recusa (e o GitHub avisa por e-mail);
  - já publicou nesse dia (stories/publicados.json) → não publica de novo;
  - data em "pular" no modelo.json, ou variável STORIES_ATIVO=nao → não publica;
  - --esperar segura até a hora do modelo (09:00 de São Luís); se o GitHub atrasar, publica assim que rodar,
    até as 20h — depois disso desiste do dia.
A Meta baixa a imagem pelo link público do repositório (raw.githubusercontent.com, fixo no commit).
"""
import argparse
import json
import os
import time
from datetime import date, datetime

from publicar import carregar_config, chamar, esperar_pronto, url_publica_ok
from stories_comum import (APROVACAO, FUSO, IMAGENS, REGISTRO, digital, hoje, ler_json, ler_modelo,
                           story_do_dia)

LIMITE_HORA = 20


def base_publica() -> str:
    if os.environ.get("IG_STORY_BASE_URL"):
        return os.environ["IG_STORY_BASE_URL"].rstrip("/")
    repo, sha = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA")
    return f"https://raw.githubusercontent.com/{repo}/{sha}/automacao-instagram/stories/imagens" if repo and sha else ""


def esperar_hora(modelo):
    h, m = map(int, modelo["hora"].split(":"))
    alvo = datetime.now(FUSO).replace(hour=h, minute=m, second=0, microsecond=0)
    falta = (alvo - datetime.now(FUSO)).total_seconds()
    if 0 < falta <= 3600:
        print(f"Aguardando {modelo['hora']} ({falta / 60:.0f} min)…", flush=True)
        time.sleep(falta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="AAAA-MM-DD (padrão: hoje em São Luís)")
    ap.add_argument("--esperar", action="store_true", help="espera até a hora do modelo antes de publicar")
    ap.add_argument("--de-verdade", action="store_true")
    a = ap.parse_args()

    modelo = ler_modelo()
    dia = date.fromisoformat(a.data) if a.data else hoje()
    if os.environ.get("STORIES_ATIVO", "").strip().lower() in ("nao", "não", "false", "0"):
        print("Stories pausados (STORIES_ATIVO=nao). Nada a fazer.")
        return
    if dia.isoformat() in modelo.get("pular", []):
        print(f"{dia} está em 'pular' no modelo.json. Nada a fazer.")
        return
    registro = ler_json(REGISTRO, {})
    if dia.isoformat() in registro:
        print(f"Story de {dia} já publicado: {registro[dia.isoformat()]}. Nada a fazer.")
        return

    sid = story_do_dia(modelo, dia)
    arq = IMAGENS / f"{sid}.jpg"
    if not arq.exists():
        raise SystemExit(f"ERRO: falta a imagem {arq.name} (rode criar_stories.py)")
    aprov = ler_json(APROVACAO, {}).get("imagens", {})
    if aprov.get(sid) != digital(arq):
        raise SystemExit(f"RECUSADO: {sid} não está aprovada (ou mudou depois da aprovação). Nada publicado.")

    base = base_publica()
    url = f"{base}/{arq.name}" if base else ""
    cfg = carregar_config()
    faltando = [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN") if not cfg[k]] + ([] if base else ["endereço público"])
    if not a.de_verdade:
        print(f"SIMULAÇÃO — {dia} ({['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'][dia.weekday()]}): "
              f"story {sid}, aprovado; às {modelo['hora']} de São Luís")
        print(f"  POST /{{IG_USER_ID}}/media  media_type=STORIES  image_url={url or '<link público>'}")
        print("  GET  /{container}?fields=status_code  →  POST /{IG_USER_ID}/media_publish")
        print("Configuração faltando para publicar: " + (", ".join(faltando) if faltando else "nada"))
        return
    if faltando:
        raise SystemExit("ERRO: falta configurar " + ", ".join(faltando))
    if a.esperar:
        esperar_hora(modelo)
    if datetime.now(FUSO).date() == dia and datetime.now(FUSO).hour >= LIMITE_HORA:
        raise SystemExit(f"ERRO: já passou das {LIMITE_HORA}h; o story de {dia} não foi publicado.")
    ruim = url_publica_ok(url)
    if ruim:
        raise SystemExit(f"ERRO: a imagem não está acessível pelo link público: {ruim}")

    uid = cfg["IG_USER_ID"]
    cont = chamar("POST", f"{uid}/media", cfg, {"media_type": "STORIES", "image_url": url})["id"]
    esperar_pronto(cont, cfg, limite=180, intervalo=5)
    mid = chamar("POST", f"{uid}/media_publish", cfg, {"creation_id": cont})["id"]
    registro[dia.isoformat()] = {"id": mid, "story": sid, "em": datetime.now(FUSO).isoformat(timespec="seconds")}
    REGISTRO.write_text(json.dumps(dict(sorted(registro.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PUBLICADO: story {sid} de {dia} (id {mid})")


if __name__ == "__main__":
    main()
