"""Testa o acesso à API do Instagram SEM publicar nada (só leitura).

    python automacao-instagram/testar_acesso.py        # usa IG_USER_ID e IG_ACCESS_TOKEN do ambiente ou do .env

Confere: token válido, conta profissional, id da conta igual ao IG_USER_ID e cota de publicação do dia.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from publicar import API, carregar_config


def get(caminho, cfg, campos):
    q = urllib.parse.urlencode(dict(campos, access_token=cfg["IG_ACCESS_TOKEN"]))
    try:
        with urllib.request.urlopen(f"{API}/{cfg['IG_API_VERSAO']}/{caminho}?{q}", timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode(errors="replace").replace(cfg["IG_ACCESS_TOKEN"], "***")[:600]


def main():
    cfg = carregar_config()
    faltando = [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN") if not cfg[k]]
    if faltando:
        sys.exit("ERRO: falta configurar " + ", ".join(faltando))
    eu, erro = get("me", cfg, {"fields": "user_id,username,account_type"})
    if erro:
        sys.exit(f"ERRO: token recusado pela API: {erro}")
    print(f"Conta: @{eu.get('username')} · tipo {eu.get('account_type')} · id {eu.get('user_id')}")
    ok = True
    if str(eu.get("user_id")) != str(cfg["IG_USER_ID"]).strip():
        print(f"ERRO: IG_USER_ID ({cfg['IG_USER_ID']}) não é o id desta conta ({eu.get('user_id')}).")
        ok = False
    if eu.get("account_type") not in ("BUSINESS", "MEDIA_CREATOR"):
        print("ERRO: a conta precisa ser profissional (Empresa ou Criador de conteúdo).")
        ok = False
    cota, erro = get(f"{cfg['IG_USER_ID']}/content_publishing_limit", cfg, {"fields": "config,quota_usage"})
    if erro:
        print(f"Aviso: não consegui ler a cota de publicação ({erro[:200]}). Confira a permissão de publicação.")
    else:
        d = (cota.get("data") or [{}])[0]
        print(f"Cota de publicação: {d.get('quota_usage', '?')} usados de {d.get('config', {}).get('quota_total', '?')} nas últimas 24 h")
    print("ACESSO OK — pronto para publicar." if ok else "Corrija os itens acima.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
