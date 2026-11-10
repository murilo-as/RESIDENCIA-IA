"""Etapa 6: escolhe uma configuração da fronteira conforme a preferência e justifica cada passo.
  qualidade -> maior nota da fronteira.
  footprint -> a de menos bytes lidos por token entre as que a faixa de erro não separa da melhor nota (tolerância = a menor das duas faixas, para que uma melhor nota muito incerta não arraste a escolha para modelos bem menores).
Sem preferência no pedido: mostra o top 3 de cada, sem escolher.
Modo de raciocínio ligado fica fora da escolha por footprint: gera mais tokens por resposta e esse custo não está nos eixos."""
import json, math, sys


def ligado(p): return bool(p["raciocinio"])


def tecnicas(id_): return [t for t in id_.split("|")[1].split("+") if t != "nenhuma"]


def _item(p):
    return {k: p[k] for k in ("id", "nota", "meio", "tag", "mem_gib", "bytes_token_gib")}


def _topo_qualidade(fr, n=3):
    return sorted(fr, key=lambda p: -p["nota"])[:n]


def _topo_footprint(fr, n=3):
    pool = [p for p in fr if not ligado(p)] or fr
    melhor = max(pool, key=lambda p: p["nota"])
    equiv = [p for p in pool if melhor["nota"] - p["nota"] <= min(melhor["meio"], p["meio"])]
    return sorted(equiv, key=lambda p: (p["bytes_token_gib"], p["mem_gib"]))[:n], melhor, len(equiv), len(pool) < len(fr)


def recomendar(par, cand):
    pref = (cand["entrada"].get("preferencia") or None)
    fr = par["fronteira"]
    if not fr:
        return {"preferencia": pref, "escolhida": None, "justificativa": [], "avisos": ["fronteira vazia: nenhuma configuração com nota"]}
    reg_q = {"passo": "6.1 qualidade", "regra": "maiores notas da fronteira", "fonte": "etapa 5", "tag": "B"}
    q = _topo_qualidade(fr)
    f, melhor, n_eq, sem_ligado = _topo_footprint(fr)
    reg_f = [{"passo": "6.2 footprint", "regra": f"entre as {n_eq} configurações cuja nota a faixa de erro não separa da melhor ({melhor['nota']:.1f}; tolerância = a menor das duas faixas, para que uma melhor nota muito incerta não arraste a escolha para modelos bem menores), as de menos bytes lidos por token",
              "fonte": "faixa ± da etapa 4", "tag": "C"}]
    if sem_ligado:
        reg_f.insert(0, {"passo": "6.2a raciocínio", "regra": "modo de raciocínio ligado fica fora do footprint: custo em tokens por resposta não estimado", "fonte": "decisão de projeto", "tag": "C"})
    out = {"preferencia": pref, "justificativa": par["regras"], "avisos": list(par["avisos"])}
    if pref == "qualidade":
        out.update(escolhida=_item(q[0]), alternativas=[_item(p) for p in q[1:]]); out["justificativa"] += [reg_q]
    elif pref == "footprint":
        out.update(escolhida=_item(f[0]), alternativas=[_item(p) for p in f[1:]]); out["justificativa"] += reg_f
    else:
        out.update(escolhida=None, top_qualidade=[_item(p) for p in q], top_footprint=[_item(p) for p in f])
        out["justificativa"] += [reg_q] + reg_f + [{"passo": "6.3 sem preferência", "regra": "o pedido não diz se prefere qualidade ou footprint: mostro as 3 melhores de cada, sem escolher", "fonte": "decisão de projeto", "tag": "C"}]
    for p in ([out["escolhida"]] if out["escolhida"] else q[:1] + f[:1]):
        if p["tag"] == "C" or p["meio"] >= 3:
            out["avisos"].append(f"nota estimada {p['nota']:.1f} ± {p['meio']:.1f} (tag {p['tag']}): conferir medindo a configuração (etapa 8)")
    if ligado_id(q[0]["id"]) and pref != "footprint":
        out["avisos"].append("a configuração de maior nota usa modo de raciocínio ligado: a nota sobe mas a resposta demora mais; esse custo não foi estimado")
    out["tecnicas_nao_medidas"] = [{k: t[k] for k in ("tecnica", "movimento", "efeito_esperado", "tag")} for t in cand.get("tecnicas_nao_medidas", [])]
    return out


def ligado_id(i): return "modo_raciocinio:ligado" in i


if __name__ == "__main__":
    print(json.dumps(recomendar(json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))), ensure_ascii=False, indent=2))
