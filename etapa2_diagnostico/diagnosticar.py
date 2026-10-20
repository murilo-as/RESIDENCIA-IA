"""Etapa 2 - Diagnóstico: o pedido vira "o que medir e dentro de quais limites". Sem LLM; só lê grade.yaml.
Devolve qualidade (benchmarks), memória (orçamento, contexto) e latência (banda, meta). Não calcula números de opções (etapa 4).
  python diagnosticar.py pedido.json [-o diagnostico.json]"""
import argparse, json, os, sys, unicodedata
import yaml

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [AQUI, os.path.join(AQUI, "..")]
from config import carregar as carregar_config
CTX_CURTO, CTX_LONGO = 4096, 32768      # hipótese (C)
REFERENCIA = "base: o mesmo modelo em 16 bits, mesmo contexto e mesmo benchmark (qualidade = razao contra a base)"


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
    if tarefa in ("codigo", "traducao") and dominio != "geral":
        avisos.append(f"{tarefa} so existe no dominio geral; dominio {dominio!r} ignorado (tarefa prevalece, C)")
        dominio = "geral"
    for t, d, regra in [(tarefa, dominio, "tarefa e dominio iguais"),
                        (tarefa, "geral", "mesma tarefa no dominio geral")]:
        if t and (t, d) in cel: return cel[(t, d)], regra, avisos
    return None, "falta medir", avisos


# Banda da máquina onde se mede (DGX Spark, especificação, B).
BANDA_MEDIDA_GB_S = 273


def diagnosticar(pedido, memoria_gb=None, banda_gb_s=None, min_tok_s=None):
    grade = yaml.safe_load(open(_achar("grade.yaml")))
    v = lambda k: (pedido.get(k) or {}).get("valor")
    avisos = list(pedido.get("avisos", []))

    tarefa, dominio = v("tarefa"), v("dominio")
    padroes = [k for k, x in (("tarefa", tarefa), ("dominio", dominio)) if x is None]
    tarefa = _n(tarefa) if tarefa else _n(grade["padroes"]["tarefa"])
    if tarefa == "uso geral": tarefa = "qa"
    dominio = _n(dominio) if dominio else _n(grade["padroes"]["dominio"])

    # qualidade
    cel, regra, av = achar_celula(grade, tarefa, dominio)
    avisos += av
    q = {"celula_pedida": f"{tarefa} x {dominio}", "padroes_aplicados": padroes, "referencia": REFERENCIA}
    if cel:
        direta = cel["medida"] == "direta" and regra == "tarefa e dominio iguais"
        q.update(benchmarks=cel["benchmarks"], celula_usada=f"{cel['tarefa']} x {cel['dominio']}",
                 medida="direta" if direta else "indireta", regra=regra, tag="B")
        q["falta"] = []
    else:
        q.update(benchmarks=[], medida="falta medir", regra=regra, falta=["nenhuma celula da grade serve a este pedido"])

    # contexto alvo
    longo = v("entrada_longa")
    ctx = {"valor": CTX_LONGO if longo else CTX_CURTO, "regra": "entrada longa" if longo else "padrao curto", "tag": "C"}

    # memória
    if memoria_gb is not None: orc, org = memoria_gb, "config.yaml"
    elif v("memoria_gb") is not None: orc, org = v("memoria_gb"), "pedido"
    else: orc, org = None, "nao informado"
    if orc is None and v("hardware"):
        avisos.append(f"hardware {v('hardware')!r} citado, mas sem GB: informe a memoria no pedido ou em config.yaml (limites.memoria_gb) para filtrar")
    mem = {"orcamento_gb": orc, "origem": org, "ctx_alvo": ctx,
           "formula": "pesos(params x bits/8) + KV(ctx, ficha) + overhead do motor <= orcamento",
           "falta": ([] if orc is not None else ["orcamento (sem ele nenhuma opcao e excluida; mostra-se a memoria de cada uma)"])
                    + ["overhead do motor (medir no Spark)"]}

    # latência
    if banda_gb_s is not None: ban, orb = banda_gb_s, "config.yaml"
    else: ban, orb = None, "nao informada"
    esc = round(ban / BANDA_MEDIDA_GB_S, 3) if ban else None
    lat = {"banda_gb_s": ban, "origem": orb, "ctx_alvo": ctx,
           "banda_medida_gb_s": BANDA_MEDIDA_GB_S, "escala_decode": esc,
           "regra_escala": "decode estimado = decode medido no Spark x (banda / banda medida); so decode, o prefill nao escala (C)",
           "formula": "tokens/s <= banda / bytes lidos por token (pesos ativos + KV no ctx); real = eta x isso",
           "meta": {"min_tok_s": min_tok_s, "regra": "config.yaml" if min_tok_s is not None else "sem limite"},
           "falta": ([] if ban is not None else ["banda (latencia so relativa, sem tokens/s absolutos)"])
                    + ["eta, fracao da banda realmente usada (medir no Spark)", "prefill: so medido (depende de calculo, nao de banda)"]}

    return {"qualidade": q, "memoria": mem, "latencia": lat,
            "repasse": {"modelo_id": (pedido.get("modelo") or {}).get("id"), "preferencia": v("preferencia"),
                        "raciocinio": v("raciocinio"), "idioma": v("idioma"),
                        "recursos": {k: (x or {}).get("valor") for k, x in (pedido.get("recursos") or {}).items()}},
            "avisos": avisos}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pedido"); ap.add_argument("--config"); ap.add_argument("-o", "--saida")
    a = ap.parse_args()
    L = carregar_config(a.config, AQUI)["limites"]
    d = diagnosticar(json.load(open(a.pedido)), L["memoria_gb"], L["banda_gb_s"], L["min_tok_s"])
    txt = json.dumps(d, ensure_ascii=False, indent=2)
    if a.saida: open(a.saida, "w").write(txt)
    print(txt)
