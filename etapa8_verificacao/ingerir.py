"""Etapa 8, parte 2: acrescenta o resultado de uma verificação à base da pipeline (etapa4_estimativa/medicao/).
  python etapa8_verificacao/ingerir.py verificacao_c8/resultado.json [--dry-run]
Grava em verificacoes.csv (nota por prova, com o que a ferramenta tinha estimado) e velocidade.csv (tok/s e eficiência da banda). O estimador lê o primeiro
quando config.yaml tem `fontes_medida: [..., verificacao]`. Linhas repetidas (mesmo modelo, nível, KV, prova e data) não são duplicadas."""
import argparse, csv, json, math, os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MED = os.path.join(RAIZ, "etapa4_estimativa", "medicao")
CAMPOS_V = ["modelo", "nivel", "kv", "raciocinio", "benchmark", "n", "acuracia", "erro_padrao", "tokens_por_resposta", "estimado", "meio_estimado", "caso", "maquina", "gpu", "llama_cpp", "gguf", "data"]
CAMPOS_S = ["modelo", "nivel", "kv", "gpu", "banda_gb_s", "tg_tok_s", "desvio", "bytes_gib", "eficiencia", "maquina", "llama_cpp", "caso", "data"]
PROVAS = {"HumanEval+": "humaneval_plus", "MBPP+": "mbpp_plus"}


def acrescentar(arq, campos, linhas, chave, dry):
    existe = [dict(l) for l in csv.DictReader(open(arq, encoding="utf-8"))] if os.path.exists(arq) else []
    ja = {tuple(l[c] for c in chave) for l in existe}
    novas = [l for l in linhas if tuple(str(l[c]) for c in chave) not in ja]
    if novas and not dry:
        novo = not os.path.exists(arq)
        with open(arq, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, campos)
            if novo: w.writeheader()
            w.writerows(novas)
    print(f"{os.path.basename(arq)}: {len(novas)} linha(s) {'a gravar' if dry else 'gravada(s)'}, {len(linhas) - len(novas)} já existia(m)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("resultado"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    r = json.load(open(a.resultado, encoding="utf-8"))
    if r.get("limite"): raise SystemExit("resultado de teste rápido (--limite): não ingerir")
    c = r["config"]
    comum = {"maquina": r.get("maquina"), "gpu": r.get("gpu"), "llama_cpp": " ".join(r.get("llama_cpp") or []), "caso": c["caso"], "data": r["data"]}
    cod, vel = [], []
    for nome, m in (r.get("codigo") or {}).items():
        if nome not in PROVAS: continue
        b = PROVAS[nome]; e = (r.get("estimado") or {}).get(b, {})
        cod.append({"modelo": c["modelo"], "nivel": c["nivel"], "kv": c["kv"], "raciocinio": c["raciocinio"], "benchmark": b, "n": m["n"], "acuracia": round(m["passou"] / m["n"], 6),
                    "erro_padrao": round(m["erro_padrao_pts"] / 100, 6), "tokens_por_resposta": m["tokens_medios"], "estimado": e.get("nota"), "meio_estimado": e.get("meio"),
                    "gguf": r["modelo"], **comum})
    if r.get("velocidade"):
        v = r["velocidade"]
        vel.append({"modelo": c["modelo"], "nivel": c["nivel"], "kv": c["kv"], "gpu": r.get("gpu"), "banda_gb_s": r["banda_gb_s"], "tg_tok_s": round(v["tg128_tok_s"], 1),
                    "desvio": round(v.get("desvio") or 0, 1), "bytes_gib": r["bytes_gib"], "eficiencia": v["eficiencia_medida"], **{k: comum[k] for k in ("maquina", "llama_cpp", "caso", "data")}})
    acrescentar(os.path.join(MED, "verificacoes.csv"), CAMPOS_V, cod, ("modelo", "nivel", "kv", "benchmark", "data"), a.dry_run)
    acrescentar(os.path.join(MED, "velocidade.csv"), CAMPOS_S, vel, ("modelo", "nivel", "kv", "gpu", "data"), a.dry_run)
    for l in cod:
        d = l["acuracia"] * 100 - (l["estimado"] or 0); dentro = l["estimado"] is not None and abs(d) <= l["meio_estimado"]
        print(f"  {l['benchmark']}: estimado {l['estimado']} ± {l['meio_estimado']} | medido {l['acuracia'] * 100:.1f} | {'dentro' if dentro else 'FORA'} da faixa")


if __name__ == "__main__":
    main()
