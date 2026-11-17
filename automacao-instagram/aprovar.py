"""Registra a aprovação de um ciclo. Rodar SÓ quando o usuário disser "aprovado <ciclo>" na conversa.

    python automacao-instagram/aprovar.py 2026-11-16-primeira-vez --por "Tauan"

Grava aprovacao.json com a impressão digital das imagens + legenda. Se algo mudar depois, a publicação recusa.
"""
import argparse
import json
from datetime import datetime

from comum import impressao_digital, ler_post, midias, pasta_ciclo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ciclo")
    ap.add_argument("--por", required=True, help="quem aprovou")
    ap.add_argument("--obs", default="", help="observação (ex.: 'aprovado com endereço')")
    a = ap.parse_args()
    ciclo = pasta_ciclo(a.ciclo)
    post = ler_post(ciclo)
    if not midias(ciclo, post):
        raise SystemExit("ERRO: ciclo sem slides/vídeo — rode criar_post.py ou criar_reel.py antes.")
    reg = {"status": "aprovado", "por": a.por, "em": datetime.now().isoformat(timespec="seconds"),
           "impressao_digital": impressao_digital(ciclo, post), "midias": len(midias(ciclo, post)), "formato": post.get("formato"), "obs": a.obs}
    (ciclo / "aprovacao.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Aprovado: {ciclo.name} por {a.por} ({reg['impressao_digital'][:12]})")


if __name__ == "__main__":
    main()
