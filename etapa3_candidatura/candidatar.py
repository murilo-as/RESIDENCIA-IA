"""Etapa 3 - Candidatura: diagnostico.json -> candidatos.json (modelo + técnicas + níveis, com o porquê). Sem LLM.
Passos: 3.1 modelos, 3.2 técnicas aplicáveis, 3.3 enumeração, 3.4 memória, 3.5 preferência, 3.6 técnicas não medidas.
  python candidatar.py diagnostico.json [-o candidatos.json]"""
import argparse, json, os, sys
import yaml

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from regras import (carregar, _achar, avalia, avalia_recursos, config_id, memoria_gib, cabe, FAVORECE, _e3, candidatar as situacao_tecnicas)

PESOS_BASE, KV_BASE = 16, 16
CABE_TXT = {True: "sim", None: "sem folga", False: "nao"}


# 3.1 modelos
def especialidades_permitidas(grade, celula):
    """Especialidades aceitas na célula ('geral' em todas; 'ferramentas' em nenhuma)."""
    tarefa = (celula or "").split(" x ")[0]
    ok = set()
    for esp, alvos in grade["especialidade"].items():
        if alvos == "todas" or (isinstance(alvos, list) and (celula in alvos or tarefa in alvos)): ok.add(esp)
    return ok


def modos_raciocinio(f, raciocinio):
    """Modos de raciocínio possíveis. [None] = sem modo; [] = o modelo não serve ao pedido."""
    t = f["tipo"]
    if t == "hibrido": return {True: ["ligado"], False: ["desligado"], None: ["desligado", "ligado"]}[raciocinio]
    if t == "thinking": return [] if raciocinio is False else [None]
    return [] if raciocinio is True else [None]


def escolher_modelos(F, grade, d, avisos):
    r = d["repasse"]; rac = r["raciocinio"]; treino = (r["recursos"] or {}).get("treino")
    fixos = r["modelo_ids"]
    if fixos:
        for i in [i for i in fixos if i not in F]: avisos.append(f"modelo {i} fora do fichas.json; ignorado")
        fixos = [i for i in fixos if i in F]
        if not fixos: raise KeyError(f"modelo {r['modelo_ids']} fora do fichas.json")
        fora = []
        if len(fixos) > 1 and treino is not True:      # variantes: o base so fica se puder treinar
            fora = [{"id": i, "motivo": "modelo base sem poder treinar", "regra": "base so entra com treino=true"} for i in fixos if F[i]["tipo"] == "base"]
            fixos = [i for i in fixos if F[i]["tipo"] != "base"] or fixos
        for i in fixos:
            if not modos_raciocinio(F[i], rac):
                avisos.append(f"{i}: tipo {F[i]['tipo']!r} nao combina com raciocinio={rac}; mantido porque o modelo foi pedido")
        return fixos, fora, "modelo fixo"
    permitido = especialidades_permitidas(grade, d["qualidade"].get("celula_usada"))
    ok, fora = [], []
    for i, f in F.items():
        if f["especialidade"] not in permitido: fora.append({"id": i, "motivo": f"especialidade {f['especialidade']!r} fora da celula", "regra": "grade.yaml:especialidade"})
        elif f["tipo"] == "base" and treino is not True: fora.append({"id": i, "motivo": "modelo base sem poder treinar", "regra": "base so entra com treino=true"})
        elif not modos_raciocinio(f, rac): fora.append({"id": i, "motivo": f"tipo {f['tipo']!r} nao combina com raciocinio={rac}", "regra": "regra de raciocinio"})
        else: ok.append(i)
    return ok, fora, "catalogo filtrado"


# 3.2/3.3 técnicas e enumeração
def niveis_pesos_kv(f, T, cat, recursos):
    """Níveis de quantização do modelo; só o baseline se a técnica não se aplica."""
    tec = T["tecnicas"]; out = {}
    for t, base in (("quantizacao_pesos", PESOS_BASE), ("quantizacao_kv", KV_BASE)):
        m, r = avalia(tec[t], f, cat), avalia_recursos(tec[t], recursos)
        vals = [v for v in tec[t]["niveis"]["valores"] if v != base]
        out[t] = ([base] + vals, _e3([m, r])) if _e3([m, r]) is not False else ([base], False)
    return out


def configuracoes(i, f, T, cat, d, ctx, orc, pref):
    recursos = {k: v for k, v in (d["repasse"]["recursos"] or {}).items()}
    tec = T["tecnicas"]; niv = niveis_pesos_kv(f, T, cat, recursos)
    modos = modos_raciocinio(f, d["repasse"]["raciocinio"]) or ([None] if not f["tipo"] == "hibrido" else ["desligado", "ligado"])
    st_modo = _e3([avalia(tec["modo_raciocinio"], f, cat), avalia_recursos(tec["modo_raciocinio"], recursos)])
    out = []
    for bp in niv["quantizacao_pesos"][0]:
        for bk in niv["quantizacao_kv"][0]:
            for modo in modos:
                tecs = ([("quantizacao_pesos", bp)] if bp != PESOS_BASE else []) + ([("quantizacao_kv", bk)] if bk != KV_BASE else []) \
                       + ([("modo_raciocinio", modo)] if modo else [])
                mem = memoria_gib(f, ctx, bp, bk)
                c = None if orc is None else cabe(mem, orc)
                sts = [niv[t][1] for t, _ in tecs if t in niv] + ([st_modo] if modo else [])
                talvez = [t for (t, _), s in zip(tecs, [niv[t][1] if t in niv else st_modo for t, _ in tecs]) if s is not True]
                fav = [t for t, n in tecs if pref and tec[t]["movimento"] in FAVORECE[pref] and not (t == "modo_raciocinio" and n == "desligado")]
                out.append({"id": config_id(i, tecs, ctx, T), "modelo": i, "tecnicas": [{"tecnica": t, "nivel": n} for t, n in tecs],
                            "memoria_min_gib": round(mem, 2), "cabe": "desconhecido" if orc is None else CABE_TXT[c],
                            "status": "aplica" if all(s is True for s in sts) else "talvez", "talvez_por": talvez, "favorece_preferencia": fav})
    return out


# técnicas aplicáveis (ou talvez) a cada modelo, com a regra de cada decisão; movimento, custo e efeito ficam no tecnicas.yaml
def decisoes(i, F, T, recursos, pref):
    out = []
    for x in situacao_tecnicas(F[i], F, T, recursos, pref):
        if x["status"] is False: continue
        out.append({"tecnica": x["tecnica"], "status": {True: "aplica", None: "talvez"}[x["status"]], "porque": x["porque"]})
    return out


REGRAS = [
    {"passo": "3.1 modelos", "regra": "modelo citado: só ele (e suas variantes); senão catálogo filtrado por especialidade da célula, tipo (base só com treino) e raciocínio", "fonte": "grade.yaml:especialidade, fichas.json"},
    {"passo": "3.2 técnicas", "regra": "aplica_em = modelo_pronto, requer_modelo (ficha) e exige x recursos do usuário, em 3 valores (sim, talvez, não); a lista por modelo guarda as que aplicam ou talvez, com a regra de cada decisão", "fonte": "tecnicas.yaml, fichas.json"},
    {"passo": "3.3 enumeração", "regra": "pesos {16,8,4} x KV {16,8,4} x modo de raciocínio (híbridos); 16 bits = sem técnica; até 3 técnicas", "fonte": "tecnicas.yaml:niveis, configuracao.max_tecnicas"},
    {"passo": "3.4 memória", "regra": "mínimo teórico (pesos + KV) acima do orçamento = sai; folga menor que 20% = 'sem folga'; orçamento desconhecido não exclui", "fonte": "fichas.json, fichas_kv.py"},
    {"passo": "3.5 preferência", "regra": "só marca as técnicas que favorecem (qualidade: Improve e Grow; footprint: Shrink e Speed-up); nunca exclui", "fonte": "regras.py:FAVORECE"},
]


def candidatar(d, F=None, T=None):
    F, T = (F, T) if F and T else carregar()
    grade = yaml.safe_load(open(_achar("grade.yaml")))
    avisos = list(d.get("avisos", []))
    ctx = d["memoria"]["ctx_alvo"]["valor"]; orc = d["memoria"]["orcamento_gb"]     # GB do pedido = GiB
    pref = d["repasse"]["preferencia"]
    modelos, fora, como = escolher_modelos(F, grade, d, avisos)
    configs, sem_memoria = [], []
    for i in modelos:
        cs = configuracoes(i, F[i], T, F, d, ctx, orc, pref)
        viaveis = [c for c in cs if c["cabe"] != "nao"]
        if not viaveis: sem_memoria.append({"id": i, "motivo": "nem a menor configuracao cabe", "minimo_gib": min(c["memoria_min_gib"] for c in cs), "regra": "memoria minima teorica"})
        configs += viaveis
    n_total = len(configs)
    ids_ok = {c["modelo"] for c in configs}
    rec = d["repasse"]["recursos"] or {}
    cand = [{"id": i, "tipo": F[i]["tipo"], "especialidade": F[i]["especialidade"], "tecnicas": decisoes(i, F, T, rec, pref)}
            for i in modelos if i in ids_ok]
    return {"entrada": {"celula": d["qualidade"].get("celula_usada"), "orcamento_gb": orc, "ctx_alvo": ctx, "preferencia": pref,
                        "raciocinio": d["repasse"]["raciocinio"], "recursos": d["repasse"]["recursos"], "modelo_fixo": d["repasse"]["modelo_ids"]},
            "regras": REGRAS,
            "resumo": {"modelos_considerados": len(modelos), "modelos_com_configuracao": len(ids_ok), "configuracoes": n_total,
                       "orcamento_desconhecido": orc is None},
            "modelos_descartados": fora + sem_memoria,
            "modelos": cand,
            "configuracoes": configs,
            "avisos": avisos + (["orcamento de memoria desconhecido: nenhuma configuracao foi excluida por memoria"] if orc is None else [])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("diagnostico"); ap.add_argument("-o", "--saida")
    a = ap.parse_args()
    r = candidatar(json.load(open(a.diagnostico)))
    txt = json.dumps(r, ensure_ascii=False, indent=1)
    if a.saida: open(a.saida, "w").write(txt)
    print(json.dumps({k: r[k] for k in ("entrada", "resumo", "avisos")}, ensure_ascii=False, indent=1))
