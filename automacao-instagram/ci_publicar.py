"""Publicação pelo GitHub Actions: o merge do pull request do post é a aprovação.

    python automacao-instagram/ci_publicar.py --antes <sha> --depois <sha>     # depois de um merge na main
    python automacao-instagram/ci_publicar.py --ciclo <nome>                   # publicação manual (workflow_dispatch)

Regras:
- só olha ciclos que MUDARAM entre --antes e --depois (push inicial não publica nada);
- pula ciclo com "publicar": false ou já publicado (publicacao.json com id);
- se não houver aprovação válida para a versão atual, registra a aprovação em nome de quem fez o merge;
- publica com publicar.py --de-verdade; as imagens vêm do endereço "raw" do repositório no commit publicado.
Saída 0 = tudo certo (ou nada a fazer), 1 = alguma publicação falhou.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

from comum import AUTO, RAIZ, impressao_digital, ler_post

CICLOS = AUTO / "ciclos"
ZEROS = "0" * 40


def ciclos_alterados(antes: str, depois: str) -> list[str]:
    if not antes or antes == ZEROS:
        print("Push inicial ou sem commit anterior: nada a publicar.")
        return []
    saida = subprocess.run(["git", "diff", "--name-only", antes, depois, "--", str(CICLOS.relative_to(RAIZ))],
                           cwd=RAIZ, capture_output=True, text=True, check=True).stdout.split()
    nomes = []
    for caminho in saida:
        partes = caminho.replace("\\", "/").split("/")
        if len(partes) >= 3 and partes[0] == "automacao-instagram" and partes[1] == "ciclos":
            if partes[2] not in nomes:
                nomes.append(partes[2])
    return nomes


def precisa_publicar(nome: str) -> tuple[bool, str]:
    ciclo = CICLOS / nome
    if not (ciclo / "post.json").exists():
        return False, "sem post.json (ciclo removido?)"
    post = ler_post(ciclo)
    if post.get("publicar") is False:
        return False, "marcado para não publicar"
    pub = ciclo / "publicacao.json"
    if pub.exists() and json.loads(pub.read_text(encoding="utf-8")).get("id"):
        return False, "já publicado"
    return True, ""


def garantir_aprovacao(nome: str, quem: str):
    ciclo = CICLOS / nome
    post = ler_post(ciclo)
    aprov = ciclo / "aprovacao.json"
    if aprov.exists():
        reg = json.loads(aprov.read_text(encoding="utf-8"))
        if reg.get("impressao_digital") == impressao_digital(ciclo, post):
            print(f"  aprovação existente vale para esta versão ({reg.get('por')})")
            return
        aprov.rename(ciclo / f"aprovacao-anterior-{datetime.now():%Y%m%d%H%M%S}.json")
    subprocess.run([sys.executable, str(AUTO / "aprovar.py"), nome, "--por", quem,
                    "--obs", "aprovado pelo merge do pull request"], check=True, cwd=RAIZ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes")
    ap.add_argument("--depois", default="HEAD")
    ap.add_argument("--ciclo", help="publica este ciclo (manual)")
    a = ap.parse_args()

    quem = os.environ.get("APROVADO_POR") or os.environ.get("GITHUB_ACTOR") or "merge no GitHub"
    repo, sha = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA")
    if repo and sha and not os.environ.get("IG_BASE_URL"):
        os.environ["IG_BASE_URL"] = f"https://raw.githubusercontent.com/{repo}/{sha}/automacao-instagram/ciclos"

    nomes = [a.ciclo] if a.ciclo else ciclos_alterados(a.antes, a.depois)
    if not nomes:
        print("Nenhum ciclo novo ou alterado.")
        return
    falhas = 0
    for nome in nomes:
        ok, motivo = precisa_publicar(nome)
        print(f"- {nome}: {'publicar' if ok else 'pular (' + motivo + ')'}", flush=True)
        if not ok:
            continue
        garantir_aprovacao(nome, quem)
        r = subprocess.run([sys.executable, str(AUTO / "publicar.py"), nome, "--de-verdade"], cwd=RAIZ)
        if r.returncode != 0:
            falhas += 1
            print(f"  FALHOU: {nome}")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
