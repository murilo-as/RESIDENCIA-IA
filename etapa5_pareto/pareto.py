"""Etapa 5: fronteira de Pareto das configurações com nota.
Eixos (todos "menor é melhor", exceto a nota): nota média nos benchmarks do diagnóstico, memória mínima (GiB), bytes lidos por token (pesos + KV, GiB) e raciocínio ligado (0/1, proxy do custo em tokens por resposta).
Bytes lidos por token é o inverso do teto de tokens/s (banda ÷ bytes) e não depende da banda do usuário."""
import json, math, sys

TAGS = "ABC"


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
            "raciocinio": int("modo_raciocinio:ligado" in e["id"])}


def domina(a, b):
    menor = ("mem_gib", "bytes_token_gib", "raciocinio")
    ge = a["nota_rank"] >= b["nota_rank"] and all(a[k] <= b[k] for k in menor)
    return ge and (a["nota_rank"] > b["nota_rank"] or any(a[k] < b[k] for k in menor))


def pareto(est):
    pontos, fora = [], []
    for e in est["estimativas"]:
        q, x = agregar(e), eixos(e)
        if q is None: fora.append({"id": e["id"], "motivo": e.get("sem_nota_motivo", "sem nota em algum benchmark")})
        elif isinstance(x, str): fora.append({"id": e["id"], "motivo": x})
        else: pontos.append({"id": e["id"], "modelo": e["modelo"], **q, **x})
    for p in pontos:
        p["dominada_por"] = [o["id"] for o in pontos if o is not p and domina(o, p)]
    fr = sorted((p for p in pontos if not p["dominada_por"]), key=lambda p: -p["nota"])
    dom = [p for p in pontos if p["dominada_por"]]
    return {"entrada": {"benchmarks": est["entrada"]["benchmarks"], "eixos": ["nota (maior)", "mem_gib (menor)", "bytes_token_gib (menor)", "raciocinio ligado (menor)"]},
            "regras": [{"passo": "5.1 nota", "regra": "média simples das notas dos benchmarks do diagnóstico; faixa = raiz da soma dos quadrados das faixas ÷ n; tag = a pior das tags",
                        "fonte": "etapa 4 (estimar_qualidade)", "tag": "C"},
                       {"passo": "5.2 eixos", "regra": "memória = mínimo teórico (pesos + KV); velocidade = bytes lidos por token (pesos + KV no contexto alvo), inverso do teto de tokens/s; raciocínio ligado = 1 (gera mais tokens por resposta; sem estimativa do custo, então não pode dominar nem ser dominado só por nota); configurações que não cabem ou não atingem a meta saem",
                        "fonte": "etapa 4, fórmulas de banda", "tag": "B"},
                       {"passo": "5.3 dominância", "regra": "A domina B se é melhor ou igual nos quatro eixos e melhor em pelo menos um, com o valor central da nota; a faixa de erro não entra, exceto quando a nota vem do prior global (sem nenhuma medida da linha): aí vale o piso (nota − faixa), para que um palpite alto não domine",
                        "fonte": "definição de Pareto", "tag": "B"}],
            "resumo": {"avaliadas": len(est["estimativas"]), "na_fronteira": len(fr), "dominadas": len(dom), "fora": len(fora)},
            "fronteira": fr, "dominadas": dom, "fora": fora,
            "avisos": []}


if __name__ == "__main__":
    print(json.dumps(pareto(json.load(open(sys.argv[1]))), ensure_ascii=False, indent=2))
