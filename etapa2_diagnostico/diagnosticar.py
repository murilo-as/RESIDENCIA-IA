"""Etapa 2 - Diagnóstico: o pedido vira "o que medir e dentro de quais limites". Sem LLM; só lê grade.yaml.
Devolve qualidade (benchmarks), memória (orçamento, contexto) e latência (banda, meta). Não calcula números de opções (etapa 4).
  python diagnosticar.py pedido.json [-o diagnostico.json]"""
import argparse, json, os, sys, unicodedata
import yaml

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [AQUI, os.path.join(AQUI, "..")]
from config import carregar as carregar_config
CTX_CURTO, CTX_LONGO = 4096, 32768      # hipótese


def _achar(nome):
    for d in (AQUI, os.path.join(AQUI, "data"), os.path.join(AQUI, "..", "data")):
        p = os.path.join(d, nome)
        if os.path.exists(p): return p
    raise FileNotFoundError(f"{nome} nao encontrado perto de {AQUI}")


def _n(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def achar_celula(grade, tarefa, dominio):
    """Célula pedida, ou o fallback do grade.yaml. Retorna (célula|None, regra, avisos)."""
    cel = {(_n(c["tarefa"]), _n(c["dominio"])): c for c in grade["celulas"]}
    avisos = []
    for t, d, regra in [(tarefa, dominio, "tarefa e dominio iguais"),
                        (tarefa, "geral", "mesma tarefa no dominio geral")]:
        if t and (t, d) in cel: return cel[(t, d)], regra, avisos
    return None, "falta medir", avisos




def _ids_modelo(m):
    """Ids do modelo pedido (lista); aceita pedido antigo com um só "id"."""
    m = m or {}
    return m.get("ids") or ([m["id"]] if m.get("id") else [])


def diagnosticar(pedido, memoria_gb=None, banda_gb_s=None, min_tok_s=None, folga_memoria=None, eficiencia_banda=None):
    grade = yaml.safe_load(open(_achar("grade.yaml")))
    v = lambda k: (pedido.get(k) or {}).get("valor")
    avisos = list(pedido.get("avisos", []))

    tarefa, dominio = v("tarefa"), v("dominio")
    padroes = [k for k, x in (("tarefa", tarefa), ("dominio", dominio)) if x is None]
    tarefa = _n(tarefa) if tarefa else _n(grade["padroes"]["tarefa"])
    dominio = _n(dominio) if dominio else _n(grade["padroes"]["dominio"])

    # qualidade
    cel, regra, av = achar_celula(grade, tarefa, dominio)
    avisos += av
    q = {"celula_pedida": f"{tarefa} x {dominio}", "padroes_aplicados": padroes}
    if cel:
        direta = cel["medida"] == "direta" and regra == "tarefa e dominio iguais"
        q.update(benchmarks=cel["benchmarks"], celula_usada=f"{cel['tarefa']} x {cel['dominio']}",
                 medida="direta" if direta else "indireta", regra=regra)
    else:
        q.update(benchmarks=[], medida="falta medir", regra=regra)

    # contexto alvo
    longo = v("entrada_longa")
    ctx = {"valor": CTX_LONGO if longo else CTX_CURTO, "regra": "entrada longa" if longo else "padrao curto"}

    # memória
    if memoria_gb is not None: orc, org = memoria_gb, "config.yaml"
    elif v("memoria_gb") is not None: orc, org = v("memoria_gb"), "pedido"
    else: orc, org = None, "nao informado"
    if orc is None and v("hardware"):
        avisos.append(f"hardware {v('hardware')!r} citado, mas sem GB: informe a memoria no pedido ou em config.yaml (limites.memoria_gb) para filtrar")
    mem = {"orcamento_gb": orc, "origem": org, "ctx_alvo": ctx, "folga": folga_memoria}

    # latência
    if banda_gb_s is not None: ban, orb = banda_gb_s, "config.yaml"
    else: ban, orb = None, "nao informada"
    lat = {"banda_gb_s": ban, "origem": orb, "ctx_alvo": ctx, "eficiencia_banda": eficiencia_banda,
           "meta": {"min_tok_s": min_tok_s, "regra": "config.yaml" if min_tok_s is not None else "sem limite"}}

    return {"qualidade": q, "memoria": mem, "latencia": lat,
            "repasse": {"modelo_ids": _ids_modelo(pedido.get("modelo")), "preferencia": v("preferencia"),
                        "raciocinio": v("raciocinio"),
                        "recursos": {k: (x or {}).get("valor") for k, x in (pedido.get("recursos") or {}).items()}},
            "avisos": avisos}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pedido"); ap.add_argument("--config"); ap.add_argument("-o", "--saida")
    a = ap.parse_args()
    L = carregar_config(a.config, AQUI)["limites"]
    d = diagnosticar(json.load(open(a.pedido)), L["memoria_gb"], L["banda_gb_s"], L["min_tok_s"], L["folga_memoria"], L["eficiencia_banda"])
    txt = json.dumps(d, ensure_ascii=False, indent=2)
    if a.saida: open(a.saida, "w").write(txt)
    print(txt)
