"""Etapa 4 - Qualidade: nota(modelo, bits, benchmark) = nota em 16 bits x razão da quantização (queda sempre relativa ao mesmo modelo em 16 bits).
Cascata: medido (A) > irmão, razão da âncora (C) > curva em log do tamanho (C) > sem dado. Nota em 16 bits publicada (B): só MMLU do Qwen3.
A forma da queda em 4 bits vem do artigo 2505.02214 (data/curva_forma_qwen3.csv); o valor, da nossa âncora.
resultados.csv: modelo,nivel(f16|q8_0|q4_k_m),benchmark,n,acuracia(0-1),erro_padrao
  python estimar_qualidade.py ID BITS BENCHMARK [-r resultados.csv]
  python estimar_qualidade.py --loo ID [-r resultados.csv]"""
import argparse, bisect, csv, json, math, os

AQUI = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(AQUI, "..", "data")
RESULTADOS = os.path.join(AQUI, "medicao", "resultados.csv")
NIVEL_BITS = {"f16": 16, "q8_0": 8, "q4_k_m": 4}


def fichas():
    return json.load(open(os.path.join(DADOS, "fichas.json"), encoding="utf-8"))["fichas"]


def tam(f):
    return f["params"].get("texto") or f["params"]["total"]


def grupo(f):
    return "base" if f["tipo"] == "base" else "pos"


def linha(f):
    return (f["familia"], f["geracao"], f["especialidade"], grupo(f))


def ler_medicoes(caminho, F):
    M = {}
    for r in csv.DictReader(open(caminho, encoding="utf-8")):
        if r["benchmark"].endswith("_strict"):
            continue
        i = r["modelo"] if r["modelo"] in F else "Qwen/" + r["modelo"]
        M[(i, NIVEL_BITS[r["nivel"]], r["benchmark"])] = {"valor": float(r["acuracia"]), "n": int(r["n"]),
                                                          "ep": float(r["erro_padrao"]) if r["erro_padrao"] else None}
    return M


def ler_forma(F):
    c = {"base": [], "pos": []}
    for r in csv.DictReader(open(os.path.join(DADOS, "curva_forma_qwen3.csv"), encoding="utf-8")):
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


def irmaos(F, i):
    """Mesma arquitetura e tamanho (outro tipo, geração ou especialidade). Mais parecidos primeiro."""
    f = F[i]
    a = f["arquitetura"]
    out = [j for j, g in F.items() if j != i and g["familia"] == f["familia"] and g["arquitetura"]["arch"] == a["arch"]
           and g["arquitetura"]["camadas_por_tipo"] == a["camadas_por_tipo"] and abs(tam(g) / tam(f) - 1) < 0.01]
    return sorted(out, key=lambda j: (F[j]["especialidade"] != f["especialidade"], F[j]["geracao"] != f["geracao"], F[j]["tipo"] != f["tipo"]))


def razao_medida(M, i, bits, b):
    x, y = M.get((i, bits, b)), M.get((i, 16, b))
    return x["valor"] / y["valor"] if x and y and y["valor"] else None


def publicado(i, b, formas):
    if b == "mmlu":
        for g in formas.values():
            for _, _, n16, j in g:
                if j == i:
                    return {"valor": n16, "tag": "B", "metodo": "publicado", "fonte": "arXiv 2505.02214, MMLU 5-shot, 16 bits"}


def nota16(F, M, i, b, formas):
    m = M.get((i, 16, b))
    if m:
        return {"valor": m["valor"], "tag": "A", "metodo": "medido"}
    p = publicado(i, b, formas)
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
    ap.add_argument("--loo", metavar="ID"); ap.add_argument("-r", "--resultados", default=RESULTADOS)
    a = ap.parse_args()
    F = fichas()
    M, formas = ler_medicoes(a.resultados, F), ler_forma(F)
    nome = lambda x: x if x in F else "Qwen/" + x
    if a.loo:
        imprimir_loo(nome(a.loo), loo(F, M, nome(a.loo), formas))
    else:
        print(json.dumps(estimar(F, M, nome(a.id), a.bits, a.benchmark, formas), ensure_ascii=False, indent=1))
