"""Testa o acesso à API do Instagram SEM publicar nada (só leitura).

    python automacao-instagram/testar_acesso.py        # usa IG_USER_ID, IG_ACCESS_TOKEN e IG_API_HOST do ambiente/.env

Confere: token válido, id da conta do Instagram, permissões e cota de publicação do dia.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from publicar import carregar_config


def get(caminho, cfg, campos):
    q = urllib.parse.urlencode(dict(campos, access_token=cfg["IG_ACCESS_TOKEN"]))
    try:
        with urllib.request.urlopen(f"{cfg['API']}/{cfg['IG_API_VERSAO']}/{caminho}?{q}", timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode(errors="replace").replace(cfg["IG_ACCESS_TOKEN"], "***")[:600]


def main():
    cfg = carregar_config()
    faltando = [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN") if not cfg[k]]
    if faltando:
        sys.exit("ERRO: falta configurar " + ", ".join(faltando))
    print(f"Caminho: login do {'Facebook (graph.facebook.com)' if cfg['IG_API_HOST'] == 'facebook' else 'Instagram (graph.instagram.com)'}")
    ok = True

    conta, erro = get(cfg["IG_USER_ID"], cfg, {"fields": "username,name"})
    if erro:
        sys.exit(f"ERRO: a API recusou ler a conta {cfg['IG_USER_ID']}: {erro}")
    print(f"Conta do Instagram: @{conta.get('username')} ({conta.get('name', '')}) · id {conta.get('id')}")

    if cfg["IG_API_HOST"] == "facebook":
        perms, erro = get("me/permissions", cfg, {})
        if erro:
            print(f"Aviso: não consegui ler as permissões ({erro[:200]})")
        else:
            dadas = {p["permission"] for p in perms.get("data", []) if p.get("status") == "granted"}
            for p in ("instagram_basic", "instagram_content_publish", "pages_show_list", "pages_read_engagement"):
                print(f"  {'✓' if p in dadas else '✗'} {p}")
                ok &= p in dadas
        dbg, erro = get("debug_token", cfg, {"input_token": cfg["IG_ACCESS_TOKEN"]})
        if not erro:
            exp = dbg.get("data", {}).get("expires_at")
            if exp == 0:
                print("Token: não expira")
            elif exp:
                from datetime import datetime
                print(f"Token: expira em {datetime.fromtimestamp(exp):%d/%m/%Y %H:%M}")
                if (datetime.fromtimestamp(exp) - datetime.now()).days < 7:
                    print("  ATENÇÃO: token curto (expira em menos de 7 dias). Gere o de longa duração (60 dias).")
    else:
        eu, erro = get("me", cfg, {"fields": "user_id,account_type"})
        if not erro:
            if str(eu.get("user_id")) != cfg["IG_USER_ID"]:
                print(f"ERRO: IG_USER_ID ({cfg['IG_USER_ID']}) não é o id da conta do token ({eu.get('user_id')}).")
                ok = False
            if eu.get("account_type") not in ("BUSINESS", "MEDIA_CREATOR"):
                print("ERRO: a conta precisa ser profissional (Empresa ou Criador de conteúdo).")
                ok = False

    cota, erro = get(f"{cfg['IG_USER_ID']}/content_publishing_limit", cfg, {"fields": "config,quota_usage"})
    if erro:
        print(f"ERRO: sem acesso à publicação ({erro[:200]})")
        ok = False
    else:
        d = (cota.get("data") or [{}])[0]
        print(f"Cota de publicação: {d.get('quota_usage', '?')} usados de {d.get('config', {}).get('quota_total', '?')} nas últimas 24 h")
    print("ACESSO OK — pronto para publicar." if ok else "Corrija os itens acima.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
