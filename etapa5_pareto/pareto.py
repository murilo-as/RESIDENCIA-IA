"""Etapa 5: fronteira de Pareto das configurações com nota.
Eixos (todos "menor é melhor", exceto a nota): nota média nos benchmarks do diagnóstico, memória mínima (GiB), bytes lidos por token (pesos + KV, GiB) e raciocínio ligado (0/1, proxy do custo em tokens por resposta).
Bytes lidos por token é o inverso do teto de tokens/s (banda ÷ bytes) e não depende da banda do usuário."""
import json, math, sys

TAGS = "ABC"
EMPATE_MESMO_MODELO = 0.5      # pts. HIPÓTESE: no mesmo modelo o erro da nota base é comum, então só a diferença da técnica conta; abaixo disso é empate


def agregar(e):
    q = e["qualidade"]
    if not q or any(not v for v in q.values()):
        return None
    n = len(q)
    nota = round(100 * sum(v["valor"] for v in q.values()) / n, 2)
    meio = round(math.sqrt(sum(v["meio_pts"] ** 2 for v in q.values())) / n, 2)
    sem_base = any("prior_global" in (v.get("fonte") or "") for v in q.values())
    return {"nota": nota, "meio": meio, "sem_base": sem_base, "nota_rank": round(nota - meio, 2) if sem_base else nota,
            "tag": max((v["tag"] for v in q.values()), key=TAGS.index), "benchmarks": list(q)}


def eixos(e):
    l = e["latencia_decodificacao"]
    if l["bytes_pesos_gib"] is None:
        return "sem tamanho de parâmetros na ficha do modelo"
    if e["memoria"]["cabe"] == "nao" or e["atende_meta"] == "nao":
        return "não cabe na memória ou não atinge a meta de tokens/s"
    return {"mem_gib": e["memoria"]["min_gib"], "bytes_token_gib": round(l["bytes_pesos_gib"] + l["bytes_kv_gib_no_ctx"], 3),
            "raciocinio": e["raciocinio"], "tok_s": l["tok_s_estimado"], "atende_meta": e["atende_meta"]}


def tolerancia(a, b):
    """Diferença de nota que não separa duas configurações. No mesmo modelo o erro da nota base é comum às duas, então só a diferença da técnica conta."""
    return EMPATE_MESMO_MODELO if a["modelo"] == b["modelo"] else min(a["meio"], b["meio"])


def domina(a, b):
    """Nota dentro da tolerância conta como empate: diferença menor que o erro não separa as configurações."""
    menor = ("mem_gib", "bytes_token_gib", "raciocinio")
    tol = tolerancia(a, b)
    d = a["nota_rank"] - b["nota_rank"]
    return d >= -tol and all(a[k] <= b[k] for k in menor) and (d > tol or any(a[k] < b[k] for k in menor))


def juntar(pontos):
    """Configurações com os mesmos números (variantes que herdam a nota do mesmo irmão) viram uma linha, com a lista dos equivalentes."""
    grupos = {}
    for p in pontos:
        g = grupos.setdefault((p["nota"], p["meio"], p["mem_gib"], p["bytes_token_gib"], p["raciocinio"], p["tag"]), [])
        g.append(p)
    return [{**g[0], "equivalentes": [o["modelo"] for o in g[1:]]} if len(g) > 1 else g[0] for g in grupos.values()]


def pareto(est):
    pontos, fora = [], []
    for e in est["estimativas"]:
        q, x = agregar(e), eixos(e)
        if q is None: fora.append({"id": e["id"], "motivo": e.get("sem_nota_motivo", "sem nota em algum benchmark")})
        elif isinstance(x, str): fora.append({"id": e["id"], "motivo": x})
        else: pontos.append({"id": e["id"], "modelo": e["modelo"], **q, **x})
    pontos = juntar(pontos)
    for p in pontos:
        p["dominada_por"] = [o["id"] for o in pontos if o is not p and domina(o, p)]
    fr = sorted((p for p in pontos if not p["dominada_por"]), key=lambda p: -p["nota"])
    dom = [p for p in pontos if p["dominada_por"]]
    return {"entrada": {"benchmarks": est["entrada"]["benchmarks"], "eixos": ["nota (maior)", "mem_gib (menor)", "bytes_token_gib (menor)", "raciocinio ligado (menor)"]},
            "regras": [{"passo": "5.1 nota", "regra": "média simples das notas dos benchmarks do diagnóstico; faixa = raiz da soma dos quadrados das faixas ÷ n; tag = a pior das tags",
                        "fonte": "etapa 4 (estimar_qualidade)"},
                       {"passo": "5.2 eixos", "regra": "memória = mínimo teórico (pesos + KV); velocidade = bytes lidos por token (pesos + KV no contexto alvo), inverso do teto de tokens/s; raciocínio ligado = 1, também nos modelos Thinking, que sempre raciocinam (gera mais tokens por resposta; sem estimativa do custo, então não pode dominar nem ser dominado só por nota); configurações que não cabem ou não atingem a meta saem",
                        "fonte": "etapa 4, fórmulas de banda"},
                       {"passo": "5.3 dominância", "regra": "A domina B se é melhor ou igual nos quatro eixos e melhor em pelo menos um. Entre modelos diferentes, diferença de nota menor que a menor das duas faixas é empate (decidem os outros eixos); no mesmo modelo, menos de 0,5 pt; quando a nota vem do prior global (sem medida da linha) vale o piso (nota − faixa), para que um palpite alto não domine. Configurações com os mesmos números viram uma linha, com a lista dos equivalentes",
                        "fonte": "definição de Pareto"}],
            "resumo": {"avaliadas": len(est["estimativas"]), "na_fronteira": len(fr), "dominadas": len(dom), "fora": len(fora)},
            "fronteira": fr, "dominadas": dom, "fora": fora,
            "avisos": []}


if __name__ == "__main__":
    print(json.dumps(pareto(json.load(open(sys.argv[1]))), ensure_ascii=False, indent=2))
