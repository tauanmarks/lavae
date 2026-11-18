"""Publicação pelo GitHub Actions: o merge do pull request do post é a aprovação.

    python automacao-instagram/ci_publicar.py --antes <sha> --depois <sha>     # depois de um merge na main
    python automacao-instagram/ci_publicar.py --ciclo <nome>                   # publicação manual (workflow_dispatch)
    python automacao-instagram/ci_publicar.py --agendados                      # agendamento do GitHub (posts com hora marcada)

Regras:
- só olha ciclos que MUDARAM entre --antes e --depois (push inicial não publica nada);
- pula ciclo com "publicar": false ou já publicado (publicacao.json com id);
- se não houver aprovação válida para a versão atual, registra a aprovação em nome de quem fez o merge;
- ciclo com "agendar_para" (AAAA-MM-DDTHH:MM, horário de São Luís) só sai a partir dessa hora: no push ele é
  pulado se ainda for cedo, e o modo --agendados (cron do GitHub) publica os que venceram, esperando até a hora
  se faltar pouco. Agendado só sai com aprovação válida já gravada (a rotina automática grava);
- publica com publicar.py --de-verdade; as imagens vêm do endereço "raw" do repositório no commit publicado.
Saída 0 = tudo certo (ou nada a fazer), 1 = alguma publicação falhou.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from comum import AUTO, RAIZ, impressao_digital, ler_post

CICLOS = AUTO / "ciclos"
ZEROS = "0" * 40
FUSO = timezone(timedelta(hours=-3))  # São Luís, sem horário de verão
ESPERA_MAX = timedelta(minutes=30)    # o cron roda um pouco antes da hora e espera
ATRASO_MAX = timedelta(hours=10)      # agendado que passou disso não sai sozinho (avisa)


def agora():
    return datetime.now(FUSO)


def hora_agendada(post: dict):
    a = post.get("agendar_para")
    return datetime.fromisoformat(a).replace(tzinfo=FUSO) if a else None


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


def precisa_publicar(nome: str, ignorar_agenda=False) -> tuple[bool, str]:
    ciclo = CICLOS / nome
    if not (ciclo / "post.json").exists():
        return False, "sem post.json (ciclo removido?)"
    post = ler_post(ciclo)
    if post.get("publicar") is False:
        return False, "marcado para não publicar"
    pub = ciclo / "publicacao.json"
    reg = json.loads(pub.read_text(encoding="utf-8")) if pub.exists() else {}
    if reg.get("id") and (not post.get("story_chamada") or reg.get("story_id")):
        return False, "já publicado"
    hora = hora_agendada(post)
    if hora and hora > agora() and not reg.get("id") and not ignorar_agenda:
        return False, f"agendado para {hora:%d/%m %H:%M}"
    return True, ""


def aprovacao_valida(nome: str) -> bool:
    ciclo = CICLOS / nome
    aprov = ciclo / "aprovacao.json"
    if not aprov.exists():
        return False
    return json.loads(aprov.read_text(encoding="utf-8")).get("impressao_digital") == impressao_digital(ciclo, ler_post(ciclo))


def agendados() -> list[str]:
    """Ciclos com hora marcada que já venceram (ou vencem em até 30 min: espera). Mais cedo primeiro."""
    fila = []
    for d in sorted(CICLOS.iterdir()):
        if not (d / "post.json").exists():
            continue
        hora = hora_agendada(ler_post(d))
        if not hora:
            continue
        ok, motivo = precisa_publicar(d.name)
        if motivo == "já publicado" or motivo.startswith("marcado"):
            continue
        falta = hora - agora()
        if falta > ESPERA_MAX:
            continue
        if -falta > ATRASO_MAX:
            print(f"::warning::{d.name}: agendado para {hora:%d/%m %H:%M} e não saiu. Publique à mão se ainda fizer sentido.")
            continue
        fila.append((hora, d.name))
    fila.sort()
    for hora, nome in fila:
        falta = (hora - agora()).total_seconds()
        if falta > 0:
            print(f"Esperando até {hora:%H:%M} para publicar {nome} ({falta / 60:.0f} min)...", flush=True)
            time.sleep(falta)
    return [n for _, n in fila]


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
    ap.add_argument("--agendados", action="store_true", help="publica os ciclos com hora marcada que venceram")
    a = ap.parse_args()

    quem = os.environ.get("APROVADO_POR") or os.environ.get("GITHUB_ACTOR") or "merge no GitHub"
    repo = os.environ.get("GITHUB_REPOSITORY")
    # commit que está checado (no cron é a main na hora da execução, não a do disparo)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip() or os.environ.get("GITHUB_SHA")
    if repo and sha and not os.environ.get("IG_BASE_URL"):
        os.environ["IG_BASE_URL"] = f"https://raw.githubusercontent.com/{repo}/{sha}/automacao-instagram/ciclos"

    nomes = [a.ciclo] if a.ciclo else agendados() if a.agendados else ciclos_alterados(a.antes, a.depois)
    if not nomes:
        print("Nenhum ciclo novo ou alterado.")
        return
    falhas = 0
    for nome in nomes:
        # manual publica na hora, mesmo agendado; o cron já esperou a hora
        ok, motivo = precisa_publicar(nome, ignorar_agenda=bool(a.ciclo or a.agendados))
        print(f"- {nome}: {'publicar' if ok else 'pular (' + motivo + ')'}", flush=True)
        if not ok:
            continue
        if a.agendados and not aprovacao_valida(nome):
            print("  pulado: agendado sem aprovação válida para esta versão")
            falhas += 1
            continue
        garantir_aprovacao(nome, quem)
        r = subprocess.run([sys.executable, str(AUTO / "publicar.py"), nome, "--de-verdade"], cwd=RAIZ)
        if r.returncode != 0:
            falhas += 1
            print(f"  FALHOU: {nome}")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
