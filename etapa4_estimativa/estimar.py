"""Etapa 4 - Estimativa: candidatos.json -> estimativas.json (memória, latência e qualidade por configuração, com origem e tag). Sem LLM.
Fórmula onde há (memória, teto de tokens/s); medida do efeitos.csv onde existir (própria > paper > card); sem dado = nulo, nunca palpite.
  python estimar.py candidatos.json diagnostico.json [-o estimativas.json]"""
import argparse, csv, json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [AQUI, os.path.join(AQUI, "..", "etapa3_candidatura")]
from regras import carregar, _achar
from fichas_kv import kv_bytes
import estimar_qualidade as EQ

GIB = 2 ** 30
ORDEM_ORIGEM = {"propria": 0, "paper": 1, "card": 2}


def ler_efeitos():
    p = _achar("efeitos.csv", obrigatorio=False)
    idx = {}
    for r in (csv.DictReader(open(p)) if p else []):
        idx.setdefault((r["id"], r["eixo"]), []).append(r)
    return idx


def melhor(linhas, filtro=lambda r: True):
    """Linha de melhor origem (própria > paper > card) entre as que passam no filtro."""
    ok = [r for r in linhas if filtro(r)]
    return min(ok, key=lambda r: ORDEM_ORIGEM[r["origem"]]) if ok else None


def efeito(r):
    return {"valor": float(r["valor"]), "tipo": r["tipo_valor"], "origem": r["origem"], "tag": r["tag"], "fonte": r["fonte_ref"],
            "ic": [float(r["ic_baixo"]), float(r["ic_alto"])] if r["ic_baixo"] else None}


def bytes_pesos_ativos(f, bits):
    """Bytes de pesos lidos por token. Denso: todos os parâmetros de texto. MoE: só os ativos; sem o número, desconhecido."""
    p = f["params"]
    n = p.get("ativos") if p.get("moe") else (p.get("texto") or p["total"])
    return None if n is None else n * bits / 8


def nivel(c, tecnica, padrao):
    return next((t["nivel"] for t in c["tecnicas"] if t["tecnica"] == tecnica), padrao)


def nota_propria(c, F, b, qual):
    """Nota estimada por estimar_qualidade. Só cobre quantização de pesos (16/8/4), com raciocínio desligado e sem outras técnicas."""
    if not qual:
        return None
    M, formas = qual
    racio = [t["nivel"] for t in c["tecnicas"] if t["tecnica"] == "modo_raciocinio"]
    if nivel(c, "quantizacao_kv", 16) != 16 or (racio and racio[0] != "desligado") or any(t["tecnica"] not in ("quantizacao_pesos", "modo_raciocinio", "decoding_especulativo") for t in c["tecnicas"]):
        return None
    k = EQ.chave(b, M)
    e = EQ.estimar(F, M, c["modelo"], nivel(c, "quantizacao_pesos", 16), k, formas) if k else None
    if not e or e["valor"] is None:
        return None
    return {"valor": round(e["valor"], 4), "tipo": "nota_absoluta", "origem": "propria", "tag": e["tag"], "fonte": "estimar_qualidade: " + e["metodo"], "ic": None}


def estimar_config(c, f, d, efeitos, benchmarks, F=None, qual=None):
    ctx, lat = d["memoria"]["ctx_alvo"]["valor"], d["latencia"]
    bp, bk = nivel(c, "quantizacao_pesos", 16), nivel(c, "quantizacao_kv", 16)
    pesos = bytes_pesos_ativos(f, bp)
    kv = kv_bytes(f, ctx, bytes_kv=bk / 8)["total"]
    base = bytes_pesos_ativos(f, 16)
    banda = lat["banda_gb_s"]
    teto = (lambda b: round(banda * 1e9 / b, 1) if banda and b else None)
    # latência de decodificação
    l = {"bytes_pesos_gib": None if pesos is None else round(pesos / GIB, 3), "bytes_kv_gib_no_ctx": round(kv / GIB, 3),
         "teto_tok_s_so_pesos": teto(pesos), "teto_tok_s_com_kv": teto(pesos + kv) if pesos else None,
         "aceleracao_teorica_vs_16bits": round((base + kv_bytes(f, ctx)["total"]) / (pesos + kv), 2) if pesos else None,
         "tag": "B (fórmula); eta, a fração da banda realmente usada, não medido", "real": None}
    m = melhor(efeitos.get((c["id"], "latencia_decodificacao"), []), lambda r: r["tipo_valor"] == "absoluto")
    if m: l["real"] = {**efeito(m), "tok_s_na_banda_pedida": round(float(m["valor"]) * lat["escala_decode"], 1) if lat.get("escala_decode") else None,
                       "nota": "medido no Spark; escalado pela razão das bandas (C)"}
    # meta de tokens/s: o teto só com pesos é limite superior verdadeiro, então abaixo da meta é "não" com certeza
    meta = lat["meta"]["min_tok_s"]
    ref = l["real"]["tok_s_na_banda_pedida"] if l["real"] and l["real"]["tok_s_na_banda_pedida"] else None
    if meta is None: atende = "sem meta"
    elif ref is not None: atende = "sim" if ref >= meta else "nao"
    elif l["teto_tok_s_so_pesos"] is None: atende = "desconhecido"
    else: atende = "nao" if l["teto_tok_s_so_pesos"] < meta else "talvez"
    # qualidade por benchmark da célula
    q = {}
    for b in benchmarks:
        r = melhor([x for x in efeitos.get((c["id"], "qualidade"), []) if x["benchmark"] == b])
        q[b] = efeito(r) if r else nota_propria(c, F, b, qual)
    return {"id": c["id"], "modelo": c["modelo"], "memoria": {"min_gib": c["memoria_min_gib"], "cabe": c["cabe"], "tag": "B", "falta": "overhead do motor (medir no Spark)"},
            "latencia_decodificacao": l, "atende_meta": atende, "qualidade": q, "talvez_por": c["talvez_por"]}


def estimar(cand, d, F=None):
    F = F or carregar()[0]
    efeitos, benchmarks = ler_efeitos(), d["qualidade"].get("benchmarks", [])
    qual = (EQ.ler_medicoes(EQ.CSVS, F), EQ.ler_forma(F)) if EQ.CSVS else None
    est = [estimar_config(c, F[c["modelo"]], d, efeitos, benchmarks, F, qual) for c in cand["configuracoes"]]
    com_q = sum(any(v for v in e["qualidade"].values()) for e in est)
    return {"entrada": {"banda_gb_s": d["latencia"]["banda_gb_s"], "meta_tok_s": d["latencia"]["meta"]["min_tok_s"], "benchmarks": benchmarks,
                        "ctx_alvo": d["memoria"]["ctx_alvo"]["valor"]},
            "resumo": {"configuracoes": len(est), "com_qualidade": com_q, "sem_qualidade": len(est) - com_q,
                       "atende_meta": {k: sum(e["atende_meta"] == k for e in est) for k in ("sim", "talvez", "nao", "sem meta", "desconhecido")}},
            "estimativas": est,
            "avisos": ([] if com_q else ["nenhuma configuracao tem qualidade medida: o efeitos.csv nao existe ou nao cobre estes benchmarks"])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("candidatos"); ap.add_argument("diagnostico"); ap.add_argument("-o", "--saida")
    a = ap.parse_args()
    r = estimar(json.load(open(a.candidatos)), json.load(open(a.diagnostico)))
    if a.saida: open(a.saida, "w").write(json.dumps(r, ensure_ascii=False))
    print(json.dumps({k: r[k] for k in ("entrada", "resumo", "avisos")}, ensure_ascii=False, indent=1))
