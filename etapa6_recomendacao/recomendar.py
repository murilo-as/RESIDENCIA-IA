"""Etapa 6: escolhe uma configuração da fronteira conforme a preferência e justifica cada passo.
  qualidade -> maior piso (nota − faixa) da fronteira.
  footprint -> entre as que a faixa de erro não separa da melhor nota (mesma tolerância da etapa 5: a menor das duas faixas entre modelos diferentes, 0,5 pt no mesmo modelo), a de melhor posição somada em memória e em bytes lidos por token.
Sem preferência no pedido: mostra o top 3 de cada, sem escolher.
Modo de raciocínio ligado fica fora da escolha por footprint: gera mais tokens por resposta e esse custo não está nos eixos."""
import json, math, os, sys
import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "etapa5_pareto"))
from pareto import tolerancia

CUSTO = {"nenhum": 0, "leve": 1, "alto": 2, "varia": 3}
MOVIMENTOS = {"qualidade": ["Improve", "Grow"], "footprint": ["Shrink", "Speed-up"], None: ["Improve", "Grow", "Shrink", "Speed-up"]}


def ligado(p): return bool(p["raciocinio"])


def tecnicas(id_): return [t for t in id_.split("|")[1].split("+") if t != "nenhuma"]


METODOS = {"medido": "medida direta", "medido_8bits": "medida direta em 8 bits (verificação)", "interp": "curva do tamanho entre modelos medidos da mesma linha", "extrap": "curva do tamanho, fora do intervalo medido",
           "irmao_nota": "nota de modelo irmão (mesma arquitetura)", "prior_global": "prior global, sem medida na linha", "prior_global_4bits": "perda de 4 bits por prior global",
           "prior_8bits": "perda de 8 bits por prior", "razao1": "8 bits sem perda de nota", "media_classe": "perda média de 4 bits da classe de prova",
           "medido_kv": "medida direta com KV quantizado", "kv_medido": "efeito do KV medido na prova", "kv_medido_modelo": "efeito do KV medido no modelo, em outras provas",
           "kv_irmao": "efeito do KV de modelo irmão", "kv_prior": "efeito do KV: mediana dos modelos medidos", "medido_racio": "medida direta com raciocínio ligado",
           "racio_medido": "efeito do raciocínio medido na prova", "racio_medido_modelo": "efeito do raciocínio medido no modelo, em outras provas", "racio_irmao": "efeito do raciocínio de modelo irmão"}


def _metodo(m):
    return " + ".join(METODOS.get(t, f"ponte a partir da prova {t.split(':')[1]}" if t.startswith("ponte:") else t) for t in m.split("+"))


def _item(p):
    return {**{k: p[k] for k in ("id", "nota", "meio", "tag", "mem_gib", "bytes_token_gib", "tok_s", "atende_meta")},
            "origem_nota": {b: _metodo(m) for b, m in p["metodos"].items()}}


def piso(p): return p["nota"] - p["meio"]


def _topo_qualidade(fr, n=3):
    return sorted(fr, key=lambda p: -piso(p))[:n]


def _topo_footprint(fr, n=3):
    pool = [p for p in fr if not ligado(p)] or fr
    melhor = max(pool, key=lambda p: p["nota_rank"])
    equiv = [p for p in pool if melhor["nota_rank"] - p["nota_rank"] <= tolerancia(melhor, p)]
    pos = lambda k: {id(p): sum(o[k] < p[k] for o in equiv) for p in equiv}        # posição de cada uma no eixo k (0 = menor)
    pm, pb = pos("mem_gib"), pos("bytes_token_gib")
    return sorted(equiv, key=lambda p: (pm[id(p)] + pb[id(p)], p["bytes_token_gib"], p["mem_gib"]))[:n], melhor, len(equiv), len(pool) < len(fr)


def da_configuracao(id_):
    """Técnicas da configuração escolhida, com o movimento e o efeito esperado de cada uma (só a direção; o número está na nota)."""
    T = yaml.safe_load(open(os.path.join(RAIZ, "data", "tecnicas.yaml")))["tecnicas"]
    out = []
    for t in tecnicas(id_):
        nome, nivel = t.split(":")
        if nome == "modo_raciocinio" and nivel != "ligado": continue          # desligado é o padrão, não uma técnica aplicada
        d = T.get(nome, {})
        out.append({"tecnica": nome, "nivel": nivel, "movimento": d.get("movimento"), "efeito_esperado": d.get("efeito_esperado")})
    return out


def sugeridas(cand, pref, modelos):
    """Técnicas que a etapa 3 liberou para os modelos recomendados (medidas ou não), agrupadas por movimento na ordem que a preferência pede e por custo de adaptação."""
    T = yaml.safe_load(open(os.path.join(RAIZ, "data", "tecnicas.yaml")))["tecnicas"]
    por_modelo = {m["id"]: m["tecnicas"] for m in cand.get("modelos", [])}
    g = {m: {} for m in MOVIMENTOS[pref]}
    for mid in modelos:
        for t in por_modelo.get(mid, []):
            d = T[t["tecnica"]]
            if d["movimento"] not in g: continue
            x = g[d["movimento"]].setdefault(t["tecnica"], {"tecnica": t["tecnica"], "custo": d["custo_adaptacao"], "medida": d["medida_na_v1"] == "sim", "recursos": "ok",
                                                            "efeito_esperado": d["efeito_esperado"], "modelos": [], "porque": t["porque"]})
            x["modelos"].append(mid)
            if t["status"] == "talvez": x["recursos"] = "talvez"
    return {m: sorted(v.values(), key=lambda t: (CUSTO.get(t["custo"], 9), t["tecnica"])) for m, v in g.items() if v}


def _id(i): return i.split("|")[0].removeprefix("Qwen/")


def porque(e, alts, pref):
    """Frases específicas da escolha: o que ela tem e como as alternativas se comparam a ela."""
    n = lambda x: f"{x:.1f}".replace(".", ",")
    base = (f"{_id(e['id'])} tem o maior piso da fronteira (nota {n(e['nota'])} − faixa {n(e['meio'])} = {n(piso(e))})" if pref == "qualidade"
            else f"{_id(e['id'])} é a de melhor posição somada em memória ({n(e['mem_gib'])} GiB) e bytes lidos por token ({n(e['bytes_token_gib'])} GiB) entre as de nota equivalente à melhor")
    out = [base + f"; nota por: {'; '.join(f'{b}: {o}' for b, o in e['origem_nota'].items())}"]
    for a in alts:
        v = f"{_id(a['id'])}: nota {n(a['nota'])} ± {n(a['meio'])} ({n(a['nota'] - e['nota'])} pts), {n(a['mem_gib'])} GiB"
        if a.get("tok_s") and e.get("tok_s"):
            v += f", {n(a['tok_s'])} tok/s ({n(a['tok_s'] / e['tok_s'])}× a escolhida)"
        out.append("alternativa " + v)
    return out


def recomendar(par, cand):
    pref = (cand["entrada"].get("preferencia") or None)
    fr = par["fronteira"]
    if not fr:
        return {"preferencia": pref, "escolhida": None, "justificativa": [], "avisos": ["fronteira vazia: nenhuma configuração com nota"]}
    reg_q = {"passo": "6.1 qualidade", "regra": "maiores pisos (nota − faixa) da fronteira: uma nota muito incerta não ganha só por ter o palpite mais alto", "fonte": "etapa 5"}
    q = _topo_qualidade(fr)
    f, melhor, n_eq, sem_ligado = _topo_footprint(fr)
    reg_f = [{"passo": "6.2 footprint", "regra": f"entre as {n_eq} configurações cuja nota a faixa de erro não separa da melhor ({melhor['nota']:.1f}; tolerância da etapa 5: a menor das duas faixas entre modelos diferentes, 0,5 pt no mesmo modelo), a de melhor posição somada em memória e em bytes lidos por token",
              "fonte": "faixa ± da etapa 4"}]
    if sem_ligado:
        reg_f.insert(0, {"passo": "6.2a raciocínio", "regra": "modo de raciocínio ligado fica fora do footprint: custo em tokens por resposta não estimado", "fonte": "decisão de projeto"})
    out = {"preferencia": pref, "justificativa": par["regras"], "avisos": list(par["avisos"])}
    motivos = {}
    for x in par["fora"]: motivos[x["motivo"]] = motivos.get(x["motivo"], 0) + 1
    out["avisos"] += [f"{n} configurações ficaram fora da análise: {m}" for m, n in sorted(motivos.items(), key=lambda t: -t[1])]
    if pref == "qualidade":
        out.update(escolhida=_item(q[0]), alternativas=[_item(p) for p in q[1:]]); out["justificativa"] += [reg_q]
    elif pref == "footprint":
        out.update(escolhida=_item(f[0]), alternativas=[_item(p) for p in f[1:]]); out["justificativa"] += reg_f
    else:
        out.update(escolhida=None, top_qualidade=[_item(p) for p in q], top_footprint=[_item(p) for p in f])
        out["justificativa"] += [reg_q] + reg_f + [{"passo": "6.3 sem preferência", "regra": "o pedido não diz se prefere qualidade ou footprint: mostro as 3 melhores de cada, sem escolher", "fonte": "decisão de projeto"}]
    for p in ([out["escolhida"]] if out["escolhida"] else q[:1] + f[:1]):
        if p["tag"] == "C" or p["meio"] >= 3:
            out["avisos"].append(f"nota estimada {p['nota']:.1f} ± {p['meio']:.1f} (tag {p['tag']}): conferir medindo a configuração (etapa 8)")
    if ligado(q[0]) and pref != "footprint":
        out["avisos"].append("a configuração de maior nota usa modo de raciocínio ligado: a nota sobe mas a resposta demora mais; esse custo não foi estimado")
    if out["escolhida"]:
        out["porque_escolhida"] = porque(out["escolhida"], out["alternativas"], pref)
        out["tecnicas_da_configuracao"] = da_configuracao(out["escolhida"]["id"])
    mostrados = [out["escolhida"]] + out.get("alternativas", []) if out["escolhida"] else out["top_qualidade"] + out["top_footprint"]
    modelos = list(dict.fromkeys(p["id"].split("|")[0] for p in mostrados))
    out["tecnicas_sugeridas"] = sugeridas(cand, pref, modelos)
    out["justificativa"] = list(cand.get("regras", [])) + out["justificativa"]
    out["justificativa"].append({"passo": "6.4 técnicas", "regra": "técnicas que a etapa 3 liberou para os modelos recomendados (aplicam ou talvez, conforme os recursos do usuário), agrupadas por movimento (qualidade: Improve e Grow; footprint: Shrink e Speed-up; sem preferência: os quatro) e ordenadas por custo de adaptação; as medidas têm número na nota, as outras só a direção do efeito",
                                 "fonte": "tecnicas.yaml, etapa 3 (3.2)"})
    return out


if __name__ == "__main__":
    print(json.dumps(recomendar(json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))), ensure_ascii=False, indent=2))
