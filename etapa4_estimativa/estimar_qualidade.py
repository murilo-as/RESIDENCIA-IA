"""Etapa 4 - Qualidade: nota(modelo, bits, benchmark) = nota em 16 bits x razão da quantização (queda sempre relativa ao mesmo modelo em 16 bits).
Cascata: medido (A) > irmão, razão da âncora (C) > curva em log do tamanho (C) > sem dado. Nota em 16 bits publicada (B): só MMLU do Qwen3.
A forma da queda em 4 bits vem do artigo 2505.02214 (data/curva_forma_qwen3.csv); o valor, da nossa âncora.
resultados.csv: modelo,nivel(f16|q8_0|q4_k_m),benchmark,n,acuracia(0-1),erro_padrao
  python estimar_qualidade.py ID BITS BENCHMARK [-r resultados.csv ...]
  python estimar_qualidade.py --loo ID [-r resultados.csv ...]   (padrao: medicao/resultados*.csv, um por maquina)"""
import argparse, bisect, csv, glob, json, math, os

AQUI = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(AQUI, "..", "data")
CSVS = sorted(glob.glob(os.path.join(AQUI, "medicao", "resultados*.csv")))
NIVEL_BITS = {"f16": 16, "q8_0": 8, "q4_k_m": 4}
CHAVES = {"MMLU": ["mmlu"], "MedQA": ["medqa", "medqa_4options"], "PubMedQA": ["pubmedqa"], "GPQA Diamond": ["gpqa", "gpqa_diamond"], "GSM8K": ["gsm8k"],
          "MATH-500": ["math500", "math_500", "minerva_math500"], "OAB-Exams 1a fase": ["oab", "oab_exams"],
          "HumanEval+": ["humaneval_plus", "humanevalplus", "humaneval"], "MBPP+": ["mbpp_plus", "mbppplus", "mbpp"], "WMT24++": ["wmt24pp", "wmt24"]}


def fichas():
    return json.load(open(os.path.join(DADOS, "fichas.json"), encoding="utf-8"))["fichas"]


def tam(f):
    return f["params"].get("texto") or f["params"]["total"]


def grupo(f):
    return "base" if f["tipo"] == "base" else "pos"


def linha(f):
    return (f["familia"], f["geracao"], f["especialidade"], grupo(f))


def ler_medicoes(caminhos, F):
    M = {}
    for r in (row for c in ([caminhos] if isinstance(caminhos, str) else caminhos) for row in csv.DictReader(open(c, encoding="utf-8"))):
        if r["benchmark"].endswith("_strict"):
            continue
        i = r["modelo"] if r["modelo"] in F else "Qwen/" + r["modelo"]
        if i not in F:
            continue
        M[(i, NIVEL_BITS[r["nivel"]], r["benchmark"])] = {"valor": float(r["acuracia"]), "n": int(r["n"]),
                                                          "ep": float(r["erro_padrao"]) if r["erro_padrao"] else None}
    return M


def ler_forma(F):
    c = {"base": [], "pos": []}
    for r in csv.DictReader(open(os.path.join(DADOS, "curva_forma_qwen3.csv"), encoding="utf-8")):
        if r["id"] not in F:
            continue
        f = F[r["id"]]
        c[grupo(f)].append((tam(f), 1 - float(r["mmlu_gptq4"]) / float(r["mmlu_16"]), float(r["mmlu_16"]) / 100, r["id"]))
    return {g: sorted(v) for g, v in c.items()}


def curva(x, pts, plano=False):
    """Interpolação linear em log(tamanho) sobre pts [(tamanho, y)]; fora do intervalo, extrapola pelos 2 pontos da ponta (ou fica plana)."""
    if len(pts) == 1:
        return pts[0][1], "extrap"
    L = sorted((math.log(a), b) for a, b in pts)
    lx = math.log(x)
    pos = "interp" if L[0][0] <= lx <= L[-1][0] else "extrap"
    if plano and pos == "extrap":
        return (L[0][1] if lx < L[0][0] else L[-1][1]), pos
    i = min(max(bisect.bisect_right([a for a, _ in L], lx) - 1, 0), len(L) - 2)
    (x0, y0), (x1, y1) = L[i], L[i + 1]
    return y0 + (y1 - y0) * (lx - x0) / (x1 - x0), pos


def forma(f, formas):
    return curva(tam(f), [(a, q) for a, q, _, _ in formas[grupo(f)]], plano=True)[0]


def forma_arq(f):
    """Dimensões que definem a arquitetura (a contagem de parâmetros não entra: o Base do Qwen3-1.7B tem 1,72B e o pós-treino, 2,03B, na mesma arquitetura)."""
    a, p = f["arquitetura"], f["params"]
    return (a["arch"], a["camadas"], json.dumps(a["camadas_por_tipo"], sort_keys=True), a["hidden"], a["q_heads"], a["kv_heads"], a["head_dim"],
            p.get("moe"), p.get("experts"), p.get("experts_por_token"))


def irmaos(F, i):
    """Mesma família e mesma arquitetura (outro tipo, geração ou especialidade). Mais parecidos primeiro."""
    f = F[i]
    out = [j for j, g in F.items() if j != i and g["familia"] == f["familia"] and forma_arq(g) == forma_arq(f)]
    return sorted(out, key=lambda j: (F[j]["especialidade"] != f["especialidade"], F[j]["geracao"] != f["geracao"], F[j]["tipo"] != f["tipo"]))


def razao_medida(M, i, bits, b):
    x, y = M.get((i, bits, b)), M.get((i, 16, b))
    return x["valor"] / y["valor"] if x and y and y["valor"] else None


def chave(b, M):
    """Nome do benchmark da grade no resultados.csv (o primeiro que tem medida)."""
    ks = {k[2] for k in M}
    return next((c for c in CHAVES.get(b, [b.lower()]) if c in ks), None)


def publicado(i, b, formas, M):
    """MMLU 16 bits do artigo + deslocamento da nossa amostra (media de nossa medida menos o publicado, nas outras ancoras Qwen3)."""
    if b != "mmlu":
        return None
    pub = {j: n16 for g in formas.values() for _, _, n16, j in g}
    d = [M[(j, 16, b)]["valor"] - pub[j] for j in pub if j != i and (j, 16, b) in M]
    if i in pub and d:
        return {"valor": pub[i] + sum(d) / len(d), "tag": "C", "metodo": "publicado+desloc", "fonte": "arXiv 2505.02214 (MMLU 5-shot, 16 bits) + deslocamento da amostra"}


def nota16(F, M, i, b, formas):
    m = M.get((i, 16, b))
    if m:
        return {"valor": m["valor"], "tag": "A", "metodo": "medido"}
    p = publicado(i, b, formas, M)
    if p:
        return p
    L = linha(F[i])
    pts = [(tam(F[j]), v["valor"]) for (j, bits, bb), v in M.items() if bits == 16 and bb == b and j != i and linha(F[j]) == L]
    if len(pts) < 2:
        return None
    v, pos = curva(tam(F[i]), pts)
    return {"valor": min(max(v, 0.0), 1.0), "tag": "C", "metodo": pos}


def razao(F, M, i, bits, b, formas):
    if bits == 16:
        return {"valor": 1.0, "tag": "A", "metodo": "definicao"}
    f = F[i]
    for j in irmaos(F, i):
        r = razao_medida(M, j, bits, b)
        if r is not None:
            return {"valor": r, "tag": "C", "metodo": "irmao", "de": j, "outra_especialidade": F[j]["especialidade"] != f["especialidade"]}
    metodo = None
    cand = [(tam(F[j]), j) for j in F if j != i and linha(F[j]) == linha(f) and razao_medida(M, j, bits, b) is not None]
    if not cand:
        cand = [(tam(F[j]), j) for j in F if j != i and F[j]["familia"] == f["familia"] and F[j]["especialidade"] == f["especialidade"]
                and razao_medida(M, j, bits, b) is not None]
        metodo = "outra_geracao"
    if not cand:
        return None
    t, j = min(cand, key=lambda c: abs(math.log(c[0] / tam(f))))
    r = razao_medida(M, j, bits, b)
    if bits == 4:
        r = 1 - (1 - r) * forma(f, formas) / forma(F[j], formas)
    pos = "interp" if min(c[0] for c in cand) <= tam(f) <= max(c[0] for c in cand) else "extrap"
    return {"valor": r, "tag": "C", "metodo": metodo or pos, "de": j}


def estimar(F, M, i, bits, b, formas):
    m = M.get((i, bits, b))
    if m:
        return {"valor": m["valor"], "tag": "A", "metodo": "medido", "ep": m["ep"]}
    n = nota16(F, M, i, b, formas)
    if n is None:
        return {"valor": None, "metodo": "sem_dado", "motivo": "sem nota em 16 bits"}
    r = razao(F, M, i, bits, b, formas)
    if r is None:
        return {"valor": None, "metodo": "sem_dado", "motivo": "sem razao de quantizacao"}
    tags = {n["tag"], r["tag"]}
    return {"valor": n["valor"] * r["valor"], "tag": "C" if "C" in tags else "B" if "B" in tags else "A",
            "metodo": f'{n["metodo"]}+{r["metodo"]}', "nota16": n, "razao": r}


# ---- estimativa total: toda configuracao nao medida recebe nota, faixa (meio, em pts), tag e metodo. nivel: 0 medido, 1 curva do tamanho, 2 irmao (razao),
# 3 irmao (nota), 4 ponte entre provas, 5 prior global, 6 prior nao medido (KV, raciocinio). Faixas provisorias: 1,5x o erro medio do leave-one-out (Qwen2.5).
GERATIVOS = {"gsm8k", "math500", "humaneval_plus", "humaneval_base", "mbpp_plus", "mbpp_base", "wmt24"}
CURVA_MEIO = {"conhecimento": (1.5, 3.5), "oab": (5.0, 11.0), "gerativo": (9.0, 17.0)}
KV_PRIOR = {16: (0.0, 0.0), 8: (-0.3, 1.0), 4: (-1.5, 3.0)}          # (delta, meio) em pts: prior provisorio, nao medido


def classe(b):
    return "gerativo" if b in GERATIVOS else "oab" if b == "oab" else "conhecimento"


def tam_eff(f):
    p = f["params"]
    return math.sqrt(tam(f) * p["ativos"]) if p.get("moe") and p.get("ativos") else tam(f)


def _fit(xs, ys):
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return my, 0.0, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    return a, b, (sum((y - a - b * x) ** 2 for x, y in zip(xs, ys)) / max(n - 2, 1)) ** 0.5


def _cl(v):
    return min(max(v, 0.0), 1.0)


def nota_base(F, M, i, b, formas):
    n = nota16(F, M, i, b, formas)
    if n:
        m = n["metodo"]
        meio = 200 * (M[(i, 16, b)]["ep"] or 0.01) if m == "medido" else 2.5 if m.startswith("publicado") else CURVA_MEIO[classe(b)][0 if m == "interp" else 1]
        return {**n, "meio": meio, "nivel": 0 if m == "medido" else 1}
    for j in irmaos(F, i):
        if (j, 16, b) in M:
            meio = 15.0 if F[j]["especialidade"] != F[i]["especialidade"] else 8.0 if classe(b) == "conhecimento" else 12.0
            return {"valor": M[(j, 16, b)]["valor"], "meio": meio, "metodo": "irmao_nota", "nivel": 3}
    best = None
    for b2 in {bb for (j, bt, bb) in M if j == i and bt == 16 and bb != b}:
        pares = [(M[(j, 16, b2)]["valor"], M[(j, 16, b)]["valor"]) for j in F if j != i and (j, 16, b2) in M and (j, 16, b) in M]
        if len(pares) >= 5:
            a, c, sd = _fit(*zip(*pares))
            if best is None or sd < best[1]:
                best = (a + c * M[(i, 16, b2)]["valor"], sd, b2)
    if best:
        return {"valor": _cl(best[0]), "meio": max(4.0, 150 * best[1]), "metodo": "ponte:" + best[2], "nivel": 4}
    pts = [(math.log(tam_eff(F[j])), v["valor"]) for (j, bt, bb), v in M.items() if bt == 16 and bb == b]
    if not pts:
        return None
    if len(pts) == 1:
        return {"valor": pts[0][1], "meio": 15.0, "metodo": "prior_global", "nivel": 5}
    a, c, sd = _fit(*zip(*pts))
    return {"valor": _cl(a + c * math.log(tam_eff(F[i]))), "meio": max(10.0, 150 * sd), "metodo": "prior_global", "nivel": 5}


def razao_total(F, M, i, bits, b, formas):
    if bits == 16:
        return {"valor": 1.0, "meio": 0.0, "metodo": "definicao", "nivel": 0}
    r = razao(F, M, i, bits, b, formas)
    if r:
        m = r["metodo"]
        return {**r, "meio": 0.01 if m == "medido" else 0.02 if m == "irmao" else 0.04 if m == "outra_geracao" else 0.025,
                "nivel": 0 if m == "medido" else 2 if m == "irmao" else 1}
    if bits == 8:
        return {"valor": 1.0, "meio": 0.02, "metodo": "prior_8bits", "nivel": 5}
    ref = [(1 - v["valor"] / M[(j, 16, bb)]["valor"]) / forma(F[j], formas) for (j, bt, bb), v in M.items() if bt == 4 and (j, 16, bb) in M and M[(j, 16, bb)]["valor"]]
    return {"valor": 1 - (sum(ref) / len(ref) if ref else 0.02) * forma(F[i], formas), "meio": 0.04, "metodo": "prior_global_4bits", "nivel": 5}


def estimar_total(F, M, i, b, bits=16, kv=16, racio=None, formas=None):
    f = F[i]; m = M.get((i, bits, b))
    puro = kv == 16 and racio != "ligado" and f["tipo"] != "thinking"
    ep = 200 * (m["ep"] or 0.01) if m else None
    if m and puro:
        return {"valor": m["valor"], "meio": ep, "tag": "A", "metodo": "medido", "nivel": 0}
    if m:
        pesos = {"valor": m["valor"], "meio": ep, "metodo": "medido", "nivel": 0}
    else:
        base = nota_base(F, M, i, b, formas)
        if base is None:
            return None
        rz = razao_total(F, M, i, bits, b, formas)
        pesos = {"valor": base["valor"] * rz["valor"], "meio": (base["meio"] ** 2 + (100 * base["valor"] * rz["meio"]) ** 2) ** 0.5,
                 "metodo": base["metodo"] + "+" + rz["metodo"], "nivel": max(base["nivel"], rz["nivel"])}
    dk, mk = KV_PRIOR[kv]
    dr, mr = ((4.0, 8.0) if classe(b) == "gerativo" else (0.0, 3.0)) if (racio == "ligado" or f["tipo"] == "thinking") else (0.0, 0.0)
    prior = kv != 16 or dr or mr
    return {"valor": _cl(pesos["valor"] + (dk + dr) / 100), "meio": (pesos["meio"] ** 2 + mk ** 2 + mr ** 2) ** 0.5, "tag": "C",
            "metodo": pesos["metodo"] + ("+kv_prior" if kv != 16 else "") + ("+racio_prior" if dr or mr else ""), "nivel": max(pesos["nivel"], 6 if prior else 0)}


def loo(F, M, alvo, formas):
    M2 = {k: v for k, v in M.items() if k[0] != alvo}
    out = []
    for (i, bits, b), m in sorted(M.items()):
        if i != alvo:
            continue
        e = estimar(F, M2, alvo, bits, b, formas)
        viz = [(abs(math.log(tam(F[j]) / tam(F[alvo]))), v["valor"]) for (j, bb, bn), v in M2.items() if bb == bits and bn == b and linha(F[j]) == linha(F[alvo])]
        base = min(viz)[1] if viz else None
        pts = lambda x: None if x is None else (x - m["valor"]) * 100
        out.append({"bits": bits, "benchmark": b, "real": m["valor"], "ep_pts": None if m["ep"] is None else m["ep"] * 100,
                    "est": e["valor"], "erro_pts": pts(e["valor"]), "base": base, "erro_base_pts": pts(base), "metodo": e["metodo"]})
    return out


def imprimir_loo(alvo, linhas):
    f = lambda x, p=1: "-" if x is None else f"{x:.{p}f}"
    print(f"leave-one-out: {alvo}\nbits benchmark       real   est  erro(pts)  base  erro_base(pts)  ruido(pts)  metodo")
    for r in linhas:
        print(f'{r["bits"]:>4} {r["benchmark"]:<14} {r["real"]*100:5.1f} {f(None if r["est"] is None else r["est"]*100):>5}  {f(r["erro_pts"]):>9}  '
              f'{f(None if r["base"] is None else r["base"]*100):>4}  {f(r["erro_base_pts"]):>14}  {f(r["ep_pts"]):>10}  {r["metodo"]}')
    for b in sorted({r["benchmark"] for r in linhas}):
        for nome, filtro in (("16 bits", lambda r: r["bits"] == 16), ("<16 bits", lambda r: r["bits"] < 16)):
            c = [r for r in linhas if r["benchmark"] == b and filtro(r) and r["erro_pts"] is not None]
            if c:
                cb = [r for r in c if r["erro_base_pts"] is not None]
                mb = sum(abs(r["erro_base_pts"]) for r in cb) / len(cb) if cb else None
                print(f"{b} {nome}: erro absoluto medio {sum(abs(r['erro_pts']) for r in c) / len(c):.2f} pts (n={len(c)}); linha de base {f(mb, 2)} pts")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("id", nargs="?"); ap.add_argument("bits", nargs="?", type=int); ap.add_argument("benchmark", nargs="?")
    ap.add_argument("--loo", metavar="ID"); ap.add_argument("-r", "--resultados", nargs="+", default=CSVS)
    a = ap.parse_args()
    F = fichas()
    M, formas = ler_medicoes(a.resultados, F), ler_forma(F)
    nome = lambda x: x if x in F else "Qwen/" + x
    if a.loo:
        imprimir_loo(nome(a.loo), loo(F, M, nome(a.loo), formas))
    else:
        print(json.dumps(estimar(F, M, nome(a.id), a.bits, a.benchmark, formas), ensure_ascii=False, indent=1))
