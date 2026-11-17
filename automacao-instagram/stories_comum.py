"""Peças comuns do story diário (modelo, rodízio de frases, aprovação)."""
import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from comum import AUTO

STORIES = AUTO / "stories"
IMAGENS = STORIES / "imagens"
APROVACAO = STORIES / "aprovacao.json"
REGISTRO = STORIES / "publicados.json"
# São Luís (MA): UTC-3 o ano todo, sem horário de verão. Fuso fixo para não depender do pacote tzdata no Windows.
FUSO = timezone(timedelta(hours=-3), "America/Fortaleza")


def ler_modelo() -> dict:
    return json.loads((STORIES / "modelo.json").read_text(encoding="utf-8"))


def lista_stories(modelo: dict) -> list[dict]:
    """Todos os stories do rodízio, na ordem dia (seg→dom) e frase (1→4). id = <dia>-<n>."""
    t = modelo["textos"]
    saida = []
    for d in modelo["dias"]:
        for k, frase in enumerate(d["frases"], 1):
            saida.append({"id": f"{d['id']}-{k}", "dia": d["nome"], "prefixo": t["prefixo"], "frase": frase,
                          "chamada": t["chamada"], "preco": d["preco"],
                          "endereco": t["endereco"], "horario": t["horario"]})
    return saida


def hoje() -> date:
    return datetime.now(FUSO).date()


def story_do_dia(modelo: dict, dia: date) -> str:
    """Segunda usa os dias[0]; a frase troca a cada semana a partir de inicio_rodizio."""
    d = modelo["dias"][dia.weekday()]
    semanas = (dia - date.fromisoformat(modelo["inicio_rodizio"])).days // 7
    return f"{d['id']}-{semanas % len(d['frases']) + 1}"


def digital(arq) -> str:
    return hashlib.sha256(arq.read_bytes()).hexdigest()


def ler_json(p, padrao):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else padrao
