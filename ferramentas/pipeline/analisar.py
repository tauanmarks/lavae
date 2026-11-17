"""analisar.py — análise do material bruto antes de qualquer edição.

Uso:
  python ferramentas/pipeline/analisar.py videos-brutos/<projeto> [--modelo turbo|small] [--sem-limpeza] [--refazer]

O que faz, para cada clipe (ordem de gravação):
  1. Metadados (duração, resolução, fps, rotação, data de gravação).
  2. Áudio limpo 16 kHz (filtro passa-alta + arnndn com ferramentas/modelos/cb.rnnn).
  3. Transcrição com whisper.cpp com tempo por palavra (DTW).
  4. Mapa de fala por energia (10 ms) -> pausas REAIS entre palavras.
  5. Frases: texto + início/fim encaixados nas pausas reais = pontos de corte seguros.
  6. Takes repetidos e falsos começos entre todos os clipes, com nota e melhor take.
  7. Momentos interessantes: som sem fala (riso/reação), ação sem fala (movimento),
     frases de destaque, picos de ênfase.
  8. Clipes visualmente parecidos (regravação sem fala).
  9. Sugestão de marca pelos sinais de marcas.json.
 10. Folha de contato (miniaturas) por clipe.

Saída em <projeto>/_analise/: analise.json, relatorio.md, audio/, whisper/, miniaturas/.
"""
import argparse, json, math, re, subprocess, sys, unicodedata, wave
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
MODELOS_RNN = RAIZ / "ferramentas" / "modelos"
WHISPER_DIR = Path.home() / "AppData/Local/Programs/whisper.cpp"
WHISPER = WHISPER_DIR / "whisper-cli.exe"
MODELOS_W = {"turbo": ("ggml-large-v3-turbo-q5_0.bin", "large.v3.turbo"), "small": ("ggml-small-q5_1.bin", "small")}
EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts"}
HOP = 0.01  # 10 ms

PREENCHIMENTOS = {"é", "eh", "ah", "ahn", "hum", "hm", "tipo", "né", "então", "assim", "aí", "uhm", "ãh", "éh"}
DESTAQUE = {"olha", "nossa", "uau", "gente", "resultado", "antes", "depois", "segredo", "dica", "importante", "cuidado",
            "incrível", "amei", "odiei", "surpresa", "finalmente", "pronto", "perfeito", "socorro", "meu deus", "atenção", "nunca", "sempre"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


# ---------------------------------------------------------------- metadados
def probe(p):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(p)])
    j = json.loads(r.stdout or "{}")
    v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), {})
    a = next((s for s in j.get("streams", []) if s["codec_type"] == "audio"), None)
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = rot or int((v.get("tags") or {}).get("rotate", 0) or 0)
    w, h = v.get("width", 0), v.get("height", 0)
    if abs(rot) in (90, 270):
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fmt = j.get("format", {})
    tags = {**(fmt.get("tags") or {}), **(v.get("tags") or {})}
    criado = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time") or ""
    return {"duracao": round(float(fmt.get("duration", 0)), 3), "largura": w, "altura": h,
            "fps": round(float(num) / float(den), 3) if float(den) else 0, "rotacao": rot,
            "criado": criado, "tem_audio": a is not None}


# ---------------------------------------------------------------- áudio
def extrair_audio(clip, wav, limpar=True):
    af = "highpass=f=80"
    if limpar and (MODELOS_RNN / "cb.rnnn").exists():
        af += ",arnndn=m=cb.rnnn"  # caminho relativo: ffmpeg roda dentro de ferramentas/modelos
    r = run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vn", "-af", af, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], cwd=MODELOS_RNN)
    if r.returncode != 0:  # sem modelo de ruído / erro de filtro: extrai cru
        run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])


def ler_wav(wav):
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return x, sr


def envelope_db(x, sr):
    hop = int(sr * HOP)
    n = max(0, len(x) // hop)
    if n == 0:
        return np.array([-90.0])
    fr = x[: n * hop].reshape(n, hop)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)


def mapa_fala(db):
    """True onde há som de voz/ação. Limiar adaptativo: nível da fala (p90) - 22 dB, nunca abaixo do ruído + 6 dB."""
    fala = np.percentile(db, 90)
    ruido = np.percentile(db, 10)
    thr = max(fala - 22, ruido + 6)
    act = db > thr
    # fecha buracos < 60 ms e remove estalos < 50 ms
    act = fechar(act, 6, True)
    act = fechar(act, 5, False)
    return act, float(thr), float(fala), float(ruido)


def fechar(act, n, valor):
    """Inverte trechos de comprimento < n frames cujo valor != valor (valor=True fecha buracos)."""
    a = act.copy(); i = 0; N = len(a)
    while i < N:
        if a[i] != valor:
            j = i
            while j < N and a[j] != valor:
                j += 1
            if j - i < n and i > 0 and j < N:
                a[i:j] = valor
            i = j
        else:
            i += 1
    return a


def intervalos(act, valor=True, minimo=0.0):
    out = []; i = 0; N = len(act)
    while i < N:
        if act[i] == valor:
            j = i
            while j < N and act[j] == valor:
                j += 1
            if (j - i) * HOP >= minimo:
                out.append([round(i * HOP, 3), round(j * HOP, 3)])
            i = j
        else:
            i += 1
    return out


# ---------------------------------------------------------------- transcrição
def transcrever(wav, base, modelo, vocab=""):
    arq, dtw = MODELOS_W[modelo]
    js = Path(str(base) + ".json")
    prompt = "Olá, pessoal! Hoje eu vou mostrar pra vocês, tá? Então, vamos lá." + (f" {vocab}." if vocab else "")
    cmd = [str(WHISPER), "-m", str(WHISPER_DIR / "models" / arq), "-f", str(wav), "-l", "pt", "-ojf", "-of", str(base),
           "-t", "8", "-np", "--prompt", prompt]
    # DTW = tempo preciso por token; exige flash-attention desligado (-nfa)
    r = run(cmd + ["-dtw", dtw, "-nfa"])
    if r.returncode != 0 or not js.exists():
        print("  aviso: DTW falhou, usando tempos aproximados do whisper")
        r = run(cmd)
    if not js.exists():
        raise RuntimeError(f"whisper falhou em {wav.name}: {r.stderr[-400:]}")
    return json.loads(js.read_text(encoding="utf-8", errors="replace"))


def palavras(wj):
    """Junta tokens em palavras. Início = t_dtw do 1º token (centésimos de s), senão offsets.
    Fim provisório = início da próxima palavra, limitado pelo tamanho da palavra (o whisper estica a última palavra)."""
    out = []
    for seg in wj.get("transcription", []):
        fim_seg = seg["offsets"]["to"] / 1000
        for tk in seg.get("tokens", []):
            t = tk.get("text", "")
            if not t or t.startswith("[_") or t.startswith("<|"):
                continue
            dtw = tk.get("t_dtw", -1)
            ini = dtw / 100 if dtw is not None and dtw >= 0 else tk["offsets"]["from"] / 1000
            p = float(tk.get("p", 1))
            if t.startswith(" ") or not out:
                out.append({"w": t.strip(), "a": ini, "fim_seg": fim_seg, "p": [p], "dtw": dtw is not None and dtw >= 0})
            else:
                out[-1]["w"] += t; out[-1]["p"].append(p)
    out = [w for w in out if w["w"].strip() and re.search(r"\w", w["w"])]
    for i in range(1, len(out)):
        if out[i]["a"] < out[i - 1]["a"]:
            out[i]["a"] = out[i - 1]["a"]
    res = []
    for i, w in enumerate(out):
        letras = len(re.sub(r"\W", "", w["w"]))
        teto = w["a"] + min(1.4, 0.25 + 0.085 * letras)
        prox = out[i + 1]["a"] if i + 1 < len(out) else w["fim_seg"]
        b = max(w["a"] + 0.05, min(teto, prox))
        res.append({"w": w["w"], "a": round(w["a"], 3), "b": round(b, 3), "p": round(float(np.mean(w["p"])), 3), "dtw": w["dtw"]})
    return res


def encaixar_palavras(ws, act):
    """Encaixa cada palavra no som real: início na borda de fala mais próxima, fim no último quadro com som
    antes da próxima palavra. Resultado em a_real/b_real (precisão de 10 ms)."""
    N = len(act)
    idx = lambda t: min(N - 1, max(0, int(round(t / HOP))))
    for i, w in enumerate(ws):
        ia = idx(w["a"])
        if not act[ia]:  # começou no silêncio: procura fala até 0,3 s à frente
            k = ia
            while k < min(N - 1, ia + 30) and not act[k]:
                k += 1
            if act[k]:
                ia = k
        else:  # já está em som: recua até a borda (máx 0,15 s)
            k = ia
            while k > max(0, ia - 15) and act[k - 1]:
                k -= 1
            ia = k
        w["a_real"] = round(ia * HOP, 3)
    for i, w in enumerate(ws):
        lim = idx(min(w["b"] + 0.15, ws[i + 1]["a_real"] if i + 1 < len(ws) else w["b"] + 0.15))
        ia = idx(w["a_real"])
        ult = ia
        for k in range(ia, max(ia + 1, lim)):
            if act[k]:
                ult = k
        w["b_real"] = round(max(ult * HOP + HOP, w["a_real"] + 0.05), 3)
        if i + 1 < len(ws) and w["b_real"] > ws[i + 1]["a_real"]:
            w["b_real"] = max(w["a_real"] + 0.03, ws[i + 1]["a_real"])
    return ws


def frases(ws, pausas, dur, act=None):
    """Agrupa palavras em frases e define cortes seguros dentro das pausas reais.
    Fecha a frase em: pontuação final (. ! ? …); vírgula/dois-pontos + pausa > 0,7 s (oração completa);
    ou pausa > 1,5 s. Pausa no meio da frase SEM pontuação não abre ponto de corte (ex.: "vou ... iniciar")."""
    grupos, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        fim_pont = bool(re.search(r"[.!?…]$", w["w"]))
        virgula = bool(re.search(r"[,;:]$", w["w"]))
        prox = ws[i + 1] if i + 1 < len(ws) else None
        gap = (prox["a_real"] - w["b_real"]) if prox else 9
        if fim_pont or (virgula and gap > 0.7) or gap > 1.5 or not prox:
            grupos.append(cur); cur = []
    out = []
    for g in grupos:
        a, b = g[0]["a_real"], g[-1]["b_real"]
        # pausa real antes/depois
        antes = next((p for p in reversed(pausas) if p[1] <= a + 0.02), None)
        depois = next((p for p in pausas if p[0] >= b - 0.02), None)
        gap_antes = (antes[1] - antes[0]) if antes and a - antes[1] < 0.15 else 0.0
        gap_depois = (depois[1] - depois[0]) if depois and depois[0] - b < 0.15 else 0.0
        corte_in = round(max(antes[0] if antes else 0, a - min(0.12, gap_antes * 0.5)), 3) if gap_antes else round(max(0, a - 0.03), 3)
        corte_out = round(min(depois[1] if depois else dur, b + min(0.18, gap_depois * 0.5)), 3) if gap_depois else round(min(dur, b + 0.03), 3)
        txt = " ".join(w["w"] for w in g)
        tn = norm(txt)
        stutter = sum(1 for i in range(1, len(tn)) if tn[i] == tn[i - 1])
        fill = sum(1 for t in tn if t in PREENCHIMENTOS)
        cobertura = float(act[int(a / HOP):max(int(a / HOP) + 1, int(b / HOP))].mean()) if act is not None else 1.0
        out.append({
            "suspeita": cobertura < 0.25,  # texto sem som correspondente: possível alucinação do whisper
            "a": a, "b": b, "corte_in": corte_in, "corte_out": corte_out, "texto": txt,
            "palavras": len(g), "p": round(float(np.mean([w["p"] for w in g])), 3),
            "termina_pontuado": bool(re.search(r"[.!?…]$", g[-1]["w"])),
            "pausa_antes": round(gap_antes, 2), "pausa_depois": round(gap_depois, 2),
            "corte_seguro": gap_antes >= 0.12 and gap_depois >= 0.12,
            "truncada": a < 0.12 or b > dur - 0.12,
            "gaguejos": stutter, "preenchimentos": fill,
            "vel": round(len(g) / max(0.3, b - a), 2),
            "destaque": [d for d in DESTAQUE if re.search(r"\b" + d + r"\b", " ".join(tn))],
        })
    return out


# ---------------------------------------------------------------- imagem
def movimento_e_hash(clip, dur):
    """Movimento médio por 0,5 s e hash médio (8x8) por segundo, a partir de quadros 32x56 em cinza."""
    W, H, FPS = 32, 56, 4
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"fps={FPS},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                       capture_output=True)
    buf = np.frombuffer(r.stdout, np.uint8)
    n = len(buf) // (W * H)
    if n < 2:
        return [], []
    fr = buf[: n * W * H].reshape(n, H, W).astype(np.float32)
    diff = np.abs(np.diff(fr, axis=0)).mean((1, 2))
    mov = [round(float(diff[i:i + 2].mean()), 2) for i in range(0, len(diff), 2)]  # 0,5 s
    hashes = []
    for i in range(0, n, FPS):
        small = fr[i].reshape(8, H // 8, 8, W // 8).mean((1, 3))
        hashes.append(int("".join("1" if v else "0" for v in (small > small.mean()).flatten()), 2))
    return mov, hashes


def folha_contato(clip, dur, out):
    passo = max(2.0, dur / 48)
    n = max(1, int(dur // passo))
    linhas = max(1, math.ceil(n / 6))
    run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vf", f"fps=1/{passo:.3f},scale=180:-2,tile=6x{linhas}:padding=4:color=white",
         "-frames:v", "1", "-q:v", "4", str(out)])
    return round(passo, 2)


# ---------------------------------------------------------------- análise entre clipes
def takes_repetidos(todas):
    """todas: lista de (clip, idx, frase). Agrupa frases equivalentes e falsos começos."""
    n = len(todas)
    pai = list(range(n))
    def ach(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]; i = pai[i]
        return i
    toks = [norm(f["texto"]) for _, _, f in todas]
    falsos = {}
    for i in range(n):
        if len(toks[i]) < 2:
            continue
        for j in range(i + 1, n):
            if len(toks[j]) < 2:
                continue
            ti, tj = toks[i], toks[j]
            curto, longo = (ti, tj) if len(ti) <= len(tj) else (tj, ti)
            r = SequenceMatcher(None, ti, tj, autojunk=False).ratio()
            if len(curto) >= 3 and r >= 0.72 and len(curto) / len(longo) >= 0.6:
                pai[ach(i)] = ach(j)
            elif len(curto) >= 2 and len(curto) / len(longo) < 0.6 and longo[: len(curto)] == curto:
                k = i if curto is ti else j
                if k == i:  # o começo curto veio ANTES da frase inteira: falso começo
                    falsos[k] = j
    grupos = {}
    for i in range(n):
        grupos.setdefault(ach(i), []).append(i)
    return [g for g in grupos.values() if len(g) > 1], falsos


def nota_take(f, ultimo):
    s = 0.0
    s += 3 if f["termina_pontuado"] else 0
    s += 2 if f["corte_seguro"] else 0
    s -= 4 if f["truncada"] else 0
    s -= 1.0 * f["preenchimentos"] + 1.5 * f["gaguejos"]
    s += 3 * f["p"]
    s += 0.5 if ultimo else 0  # o último take costuma ser o "certo"
    return round(s, 2)


def sugerir_marca(texto_total, frac_sem_fala):
    try:
        M = json.loads((RAIZ / "fichas-de-marca" / "marcas.json").read_text(encoding="utf-8"))["marcas"]
    except Exception:
        return []
    tn = " " + " ".join(norm(texto_total)) + " "
    res = []
    for m in M:
        pts = 0; hits = []
        for s in m["sinais_de_deteccao"]:
            k = tn.count(" " + " ".join(norm(s)) + " ")
            if k:
                pts += k; hits.append(s)
        if m["id"] == "mao-na-massa" and frac_sem_fala > 0.5:
            pts += 3; hits.append("muito processo sem fala")
        if m["id"] == "diario-solto" and frac_sem_fala > 0.35:
            pts += 1
        res.append({"marca": m["id"], "nome": m["nome"], "pontos": pts, "sinais": hits[:8]})
    return sorted(res, key=lambda r: -r["pontos"])[:3]


def fmt(t):
    m, s = divmod(max(0, t), 60)
    return f"{int(m)}:{s:05.2f}"


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("--modelo", default="turbo", choices=list(MODELOS_W))
    ap.add_argument("--sem-limpeza", action="store_true")
    ap.add_argument("--refazer", action="store_true", help="refaz transcrições já existentes")
    ap.add_argument("--vocabulario", default="", help="nomes próprios/marcas para o whisper acertar a grafia (ex.: \"Vizzela, swatch\")")
    A = ap.parse_args()
    P = Path(A.pasta).resolve()
    O = P / "_analise"
    for d in ("audio", "whisper", "miniaturas"):
        (O / d).mkdir(parents=True, exist_ok=True)
    clips = sorted([c for c in P.iterdir() if c.suffix.lower() in EXT and c.is_file()])
    if not clips:
        sys.exit(f"Nenhum vídeo em {P}")
    metas = {c.name: probe(c) for c in clips}
    clips.sort(key=lambda c: (metas[c.name]["criado"] or "~", c.name))  # ordem de gravação

    R = {"projeto": P.name, "pasta": str(P), "clipes": [], "modelo": A.modelo}
    todas = []
    for c in clips:
        md = metas[c.name]
        print(f"→ {c.name}  {md['duracao']:.1f}s  {md['largura']}x{md['altura']}")
        item = {"clip": c.stem, "arquivo": c.name, **md, "palavras": [], "frases": [], "pausas": [], "sons_sem_fala": [],
                "acao_sem_fala": [], "picos_enfase": []}
        item["miniaturas_passo_s"] = folha_contato(c, md["duracao"], O / "miniaturas" / f"{c.stem}.jpg")
        mov, hashes = movimento_e_hash(c, md["duracao"])
        item["movimento_0_5s"] = mov; item["hash_1s"] = [str(h) for h in hashes]
        if md["tem_audio"]:
            wav = O / "audio" / f"{c.stem}.wav"
            if A.refazer or not wav.exists():
                extrair_audio(c, wav, not A.sem_limpeza)
            x, sr = ler_wav(wav)
            db = envelope_db(x, sr)
            act, thr, nivel, ruido = mapa_fala(db)
            item["nivel_fala_db"] = round(nivel, 1); item["ruido_db"] = round(ruido, 1); item["limiar_db"] = round(thr, 1)
            pausas = intervalos(act, False, 0.12)
            item["pausas"] = pausas
            base = O / "whisper" / c.stem
            wj = json.loads(Path(str(base) + ".json").read_text(encoding="utf-8", errors="replace")) if (not A.refazer and Path(str(base) + ".json").exists()) else transcrever(wav, base, A.modelo, A.vocabulario)
            ws = encaixar_palavras(palavras(wj), act)
            item["palavras"] = ws
            item["tempo_preciso"] = all(w["dtw"] for w in ws) if ws else True
            item["frases"] = frases(ws, pausas, md["duracao"], act)
            # som sem fala: regiões de som não cobertas por palavras
            cob = np.zeros(len(act), bool)
            for w in ws:
                cob[int(w["a_real"] / HOP):int(w["b_real"] / HOP) + 1] = True
            for a, b in intervalos(act & ~cob, True, 0.35):
                pico = float(db[int(a / HOP):int(b / HOP)].max())
                if pico < nivel - 15:  # fraco demais para ser riso/reação/som relevante
                    continue
                item["sons_sem_fala"].append({"a": a, "b": b, "pico_db": round(pico, 1), "nota": "riso/reação/som da ação? conferir"})
            # picos de ênfase dentro da fala (5% mais altos)
            if ws:
                ndb = np.array([db[int(w["a_real"] / HOP):max(int(w["a_real"] / HOP) + 1, int(w["b_real"] / HOP))].max() for w in ws])
                lim = np.percentile(ndb, 95)
                item["picos_enfase"] = [{"t": w["a_real"], "palavra": w["w"]} for w, v in zip(ws, ndb) if v >= lim][:10]
            fala_total = sum(f["b"] - f["a"] for f in item["frases"])
        else:
            fala_total = 0
        # ação sem fala: movimento alto (> 1,5x mediana) por >= 1,5 s fora das frases
        if mov:
            med = float(np.median(mov)) or 0.1
            alto = np.array([v > med * 1.5 for v in mov])
            for fr_ in item["frases"]:
                alto[int(fr_["a"] / 0.5):int(fr_["b"] / 0.5) + 1] = False
            for i0, i1 in intervalos(alto, True, 1.5 * HOP / 0.5):
                a, b = i0 / HOP * 0.5, i1 / HOP * 0.5
                if b - a >= 1.5:
                    item["acao_sem_fala"].append({"a": round(a, 2), "b": round(b, 2), "nota": "movimento sem fala (demonstração/B-roll?) — não cortar sem revisar"})
        item["fala_s"] = round(fala_total, 2)
        R["clipes"].append(item)
        for i, f in enumerate(item["frases"]):
            todas.append((c.stem, i, f))

    # takes repetidos
    grupos, falsos = takes_repetidos(todas)
    R["repeticoes"] = []
    for g in grupos:
        g = sorted(g)
        notas = [(k, nota_take(todas[k][2], k == g[-1])) for k in g]
        melhor = max(notas, key=lambda x: x[1])[0]
        grupo = []
        for k, nt in notas:
            clip, i, f = todas[k]
            f["take"] = "melhor" if k == melhor else "repeticao"
            f["nota_take"] = nt
            grupo.append({"clip": clip, "frase": i, "a": f["a"], "b": f["b"], "texto": f["texto"], "nota": nt, "melhor": k == melhor})
        R["repeticoes"].append(grupo)
    for k, j in falsos.items():
        todas[k][2]["take"] = todas[k][2].get("take") or "falso_comeco"
        todas[k][2]["falso_comeco_de"] = f"{todas[j][0]} @ {fmt(todas[j][2]['a'])}"

    # clipes visualmente parecidos (pouca fala)
    R["visual_parecido"] = []
    cs = R["clipes"]
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            hi = [int(h) for h in cs[i]["hash_1s"]]; hj = [int(h) for h in cs[j]["hash_1s"]]
            if len(hi) < 2 or len(hj) < 2:
                continue
            ok = sum(1 for a in hi if min(bin(a ^ b).count("1") for b in hj) <= 6)
            frac = ok / len(hi)
            if frac >= 0.6:
                R["visual_parecido"].append({"a": cs[i]["clip"], "b": cs[j]["clip"], "semelhanca": round(frac, 2)})

    texto_total = " ".join(f["texto"] for c in cs for f in c["frases"])
    dur_total = sum(c["duracao"] for c in cs) or 1
    frac_sem_fala = 1 - sum(c["fala_s"] for c in cs) / dur_total
    R["duracao_total"] = round(dur_total, 2); R["fala_total"] = round(dur_total * (1 - frac_sem_fala), 2)
    R["sugestao_marca"] = sugerir_marca(texto_total, frac_sem_fala)
    for c in cs:  # o json fica leve: hashes não são úteis depois
        c.pop("hash_1s", None)
    (O / "analise.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    (O / "relatorio.md").write_text(relatorio(R), encoding="utf-8")
    print(f"\nok: {O / 'relatorio.md'}")


def relatorio(R):
    L = [f"# Análise — {R['projeto']}", "",
         f"{len(R['clipes'])} clipes · {fmt(R['duracao_total'])} de material · {fmt(R['fala_total'])} de fala", ""]
    if R["sugestao_marca"]:
        L += ["## Marca sugerida", ""]
        for s in R["sugestao_marca"]:
            L.append(f"- **{s['nome']}** ({s['pontos']} pts) — sinais: {', '.join(s['sinais']) or '—'}")
        L.append("")
    L += ["## Clipes (ordem de gravação)", "", "| Clipe | Duração | Resolução | Fala | Gravado |", "|---|---|---|---|---|"]
    for c in R["clipes"]:
        L.append(f"| {c['clip']} | {fmt(c['duracao'])} | {c['largura']}x{c['altura']} | {fmt(c['fala_s'])} | {c['criado'][:19]} |")
    L.append("")
    if R["repeticoes"]:
        L += ["## Takes repetidos (✓ = melhor take pela nota)", ""]
        for g in R["repeticoes"]:
            for t in g:
                L.append(f"- {'✓' if t['melhor'] else '✗'} {t['clip']} {fmt(t['a'])}–{fmt(t['b'])} (nota {t['nota']}): {t['texto']}")
            L.append("")
    if R["visual_parecido"]:
        L += ["## Clipes visualmente parecidos (possível regravação)", ""]
        for v in R["visual_parecido"]:
            L.append(f"- {v['a']} ≈ {v['b']} ({int(v['semelhanca'] * 100)}%)")
        L.append("")
    L += ["## Transcrição com pontos de corte", "",
          "Legenda: ✓ melhor take · ✗ repetição · ↺ falso começo · ⚠ sem pausa para corte (não cortar aqui) · ✂ trunca no início/fim do clipe · ★ destaque · ❓ texto sem som correspondente (conferir)", ""]
    for c in R["clipes"]:
        L += [f"### {c['clip']}  ({fmt(c['duracao'])}, miniaturas a cada {c['miniaturas_passo_s']} s em _analise/miniaturas/{c['clip']}.jpg)", ""]
        if not c.get("tempo_preciso", True):
            L.append("_⚠ tempos por palavra aproximados (DTW falhou): conferir cortes de ouvido_")
        if not c["frases"]:
            L.append("_sem fala detectada_")
        for f in c["frases"]:
            marcas = ""
            marcas += {"melhor": "✓ ", "repeticao": "✗ ", "falso_comeco": "↺ "}.get(f.get("take", ""), "")
            marcas += "" if f["corte_seguro"] else "⚠ "
            marcas += "✂ " if f["truncada"] else ""
            marcas += "★ " if f["destaque"] else ""
            marcas += "❓ " if f.get("suspeita") else ""
            L.append(f"- `{fmt(f['corte_in'])}–{fmt(f['corte_out'])}` {marcas}{f['texto']}")
        for s in c["sons_sem_fala"]:
            L.append(f"- `{fmt(s['a'])}–{fmt(s['b'])}` 🔊 som sem fala ({s['pico_db']} dB) — {s['nota']}")
        for s in c["acao_sem_fala"]:
            L.append(f"- `{fmt(s['a'])}–{fmt(s['b'])}` 🎬 {s['nota']}")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    main()
