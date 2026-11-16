"""Etapa 4 - Estimativa: candidatos.json -> estimativas.json (memória, latência e qualidade por configuração, com origem e tag). Sem LLM.
Memória e latência por fórmula (tag C); qualidade pela cascata de estimar_qualidade (medida A, verificada B, estimada C).
  python estimar.py candidatos.json diagnostico.json [-o estimativas.json]"""
import argparse, json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [AQUI, os.path.join(AQUI, "..", "etapa3_candidatura")]
from regras import carregar
from fichas_kv import kv_bytes
import estimar_qualidade as EQ

GIB = 2 ** 30


def bytes_pesos_ativos(f, bits):
    """Bytes de pesos lidos por token. Denso: todos os parâmetros de texto. MoE: só os ativos; sem o número, desconhecido."""
    p = f["params"]
    n = p.get("ativos") if p.get("moe") else (p.get("texto") or p["total"])
    return None if n is None else n * bits / 8


def nivel(c, tecnica, padrao):
    return next((t["nivel"] for t in c["tecnicas"] if t["tecnica"] == tecnica), padrao)


def nota_propria(c, F, b, qual):
    """Nota estimada por estimar_qualidade.estimar_total: toda configuração não medida recebe nota, faixa (± pts), tag e método."""
    if not qual:
        return None
    M, formas = qual
    racio = [t["nivel"] for t in c["tecnicas"] if t["tecnica"] == "modo_raciocinio"]
    k = EQ.chave(b, M)
    e = EQ.estimar_total(F, M, c["modelo"], k, nivel(c, "quantizacao_pesos", 16), nivel(c, "quantizacao_kv", 16), racio[0] if racio else None, formas) if k else None
    if not e:
        return None
    v = e["valor"] * 100
    return {"valor": round(e["valor"], 4), "meio_pts": round(e["meio"], 1), "ic": [round(max(v - e["meio"], 0), 1), round(min(v + e["meio"], 100), 1)],
            "tipo": "nota_absoluta", "origem": "propria", "tag": e["tag"], "nivel_evidencia": e["nivel"], "fonte": "estimar_qualidade: " + e["metodo"]}


def estimar_config(c, f, d, benchmarks, F=None, qual=None):
    ctx, lat = d["memoria"]["ctx_alvo"]["valor"], d["latencia"]
    bp, bk = nivel(c, "quantizacao_pesos", 16), nivel(c, "quantizacao_kv", 16)
    pesos = bytes_pesos_ativos(f, bp)
    kv = kv_bytes(f, ctx, bytes_kv=bk / 8)["total"]
    base = bytes_pesos_ativos(f, 16)
    banda = lat["banda_gb_s"]
    teto = (lambda b: round(banda * 1e9 / b, 1) if banda and b else None)
    # latência de decodificação: teto = banda ÷ bytes lidos por token; estimativa = teto x eficiência_banda (config.yaml)
    ef = lat.get("eficiencia_banda")
    t_kv = teto(pesos + kv) if pesos else None
    l = {"bytes_pesos_gib": None if pesos is None else round(pesos / GIB, 3), "bytes_kv_gib_no_ctx": round(kv / GIB, 3),
         "teto_tok_s_so_pesos": teto(pesos), "teto_tok_s_com_kv": t_kv,
         "tok_s_estimado": round(t_kv * ef, 1) if t_kv and ef else None, "eficiencia_banda": ef,
         "aceleracao_teorica_vs_16bits": round((base + kv_bytes(f, ctx)["total"]) / (pesos + kv), 2) if pesos else None,
         "tag": "C (fórmula; eficiência vinda de 1 medida, Qwen3.5-35B-A3B Q4_K_M no Spark)"}
    # meta de tokens/s: o teto só com pesos é limite superior verdadeiro, então abaixo da meta é "não" com certeza
    meta = lat["meta"]["min_tok_s"]
    est = l["tok_s_estimado"]
    if meta is None: atende = "sem meta"
    elif l["teto_tok_s_so_pesos"] is None: atende = "desconhecido"
    elif l["teto_tok_s_so_pesos"] < meta: atende = "nao"
    elif est is not None and est >= meta: atende = "sim"
    else: atende = "talvez"
    # qualidade por benchmark da célula
    q = {b: nota_propria(c, F, b, qual) for b in benchmarks}
    motivo = None
    if any(v is None for v in q.values()):
        if nivel(c, "modo_raciocinio", None) == "ligado": motivo = "raciocínio ligado sem medida (nem do modelo nem de irmão, na mesma classe de prova): sem estimativa"
        elif bk == 4: motivo = "KV 4 bits sem medida e kv_heads < 8: risco de colapso (Qwen2.5 de 2 e 4 cabeças colapsou)"
    return {"id": c["id"], "modelo": c["modelo"], "memoria": {"min_gib": c["memoria_min_gib"], "cabe": c["cabe"], "tag": "C (fórmula)", "falta": "overhead do motor (medir no Spark)"},
            "latencia_decodificacao": l, "atende_meta": atende, "raciocinio": int(nivel(c, "modo_raciocinio", None) == "ligado" or f["tipo"] == "thinking"), "qualidade": q, "talvez_por": c["talvez_por"],
            **({"sem_nota_motivo": motivo} if motivo else {})}


def estimar(cand, d, F=None):
    F = F or carregar()[0]
    benchmarks = d["qualidade"].get("benchmarks", [])
    qual = (EQ.ler_medicoes(EQ.CSVS, F), EQ.ler_forma(F)) if EQ.CSVS else None
    est = [estimar_config(c, F[c["modelo"]], d, benchmarks, F, qual) for c in cand["configuracoes"]]
    com_q = sum(any(v for v in e["qualidade"].values()) for e in est)
    return {"entrada": {"banda_gb_s": d["latencia"]["banda_gb_s"], "meta_tok_s": d["latencia"]["meta"]["min_tok_s"], "benchmarks": benchmarks,
                        "ctx_alvo": d["memoria"]["ctx_alvo"]["valor"]},
            "resumo": {"configuracoes": len(est), "com_qualidade": com_q, "sem_qualidade": len(est) - com_q,
                       "atende_meta": {k: sum(e["atende_meta"] == k for e in est) for k in ("sim", "talvez", "nao", "sem meta", "desconhecido")}},
            "estimativas": est,
            "avisos": ([] if com_q else ["nenhuma configuracao tem nota: as medicoes nao cobrem estes benchmarks"])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("candidatos"); ap.add_argument("diagnostico"); ap.add_argument("-o", "--saida")
    a = ap.parse_args()
    r = estimar(json.load(open(a.candidatos)), json.load(open(a.diagnostico)))
    if a.saida: open(a.saida, "w").write(json.dumps(r, ensure_ascii=False))
    print(json.dumps({k: r[k] for k in ("entrada", "resumo", "avisos")}, ensure_ascii=False, indent=1))
