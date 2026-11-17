"""Registra a aprovação das imagens do story diário (só depois do "aprovado" do usuário).

    python automacao-instagram/aprovar_stories.py --por "Tauan"                 # aprova todas as imagens atuais
    python automacao-instagram/aprovar_stories.py --por "Tauan" --so terca-2    # aprova só algumas

Grava stories/aprovacao.json com a impressão digital de cada imagem. O robô das 9h só publica imagem cuja
impressão digital bate com a aprovada: se a imagem for refeita, precisa aprovar de novo.
"""
import argparse
import json
import sys
from datetime import datetime

from stories_comum import APROVACAO, IMAGENS, digital, ler_json, ler_modelo, lista_stories


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--por", required=True)
    ap.add_argument("--so", help="ids separados por vírgula (padrão: todas)")
    a = ap.parse_args()
    ids = [s["id"] for s in lista_stories(ler_modelo())]
    escolhidos = a.so.split(",") if a.so else ids
    faltando = [i for i in escolhidos if i not in ids or not (IMAGENS / f"{i}.jpg").exists()]
    if faltando:
        sys.exit("ERRO: sem imagem para " + ", ".join(faltando) + " (rode criar_stories.py)")
    reg = ler_json(APROVACAO, {"imagens": {}})
    for i in escolhidos:
        reg["imagens"][i] = digital(IMAGENS / f"{i}.jpg")
    reg["imagens"] = {i: reg["imagens"][i] for i in ids if i in reg["imagens"]}  # tira os que saíram do modelo
    reg.update(por=a.por, em=datetime.now().isoformat(timespec="seconds"))
    APROVACAO.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Aprovadas {len(escolhidos)} imagens por {a.por}. Total aprovado: {len(reg['imagens'])}/{len(ids)}")


if __name__ == "__main__":
    main()
