"""Etapa 1: aplica os criterios de aceite aos resultados de etapa1/resultados.csv e grava etapa1.json (status ok/pulado + motivo).
Uso: etapa1_avaliar.py <log do t3_verificar_isolamento.sbatch>"""
import csv, glob, json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(AQUI, "etapa1")
S3, S7, S14 = "Qwen2.5-3B-Instruct", "Qwen2.5-7B-Instruct", "Qwen2.5-14B-Instruct"
linhas = list(csv.DictReader(open(os.path.join(DIR, "resultados.csv")))) if os.path.exists(os.path.join(DIR, "resultados.csv")) else []
erros = open(os.path.join(DIR, "erros.log")).read() if os.path.exists(os.path.join(DIR, "erros.log")) else ""
out, relatorio = {}, []


def linha(modelo, nivel, bench):
    for r in linhas:
        if (r["modelo"], r["nivel"], r["benchmark"]) == (modelo, nivel, bench): return r


def amostras(modelo, nivel, pasta, k=3):
    arqs = sorted(glob.glob(os.path.join(DIR, "amostras", modelo, nivel, pasta, "**", "samples_*.jsonl"), recursive=True))
    return [json.loads(l) for l in open(arqs[-1])][:k] if arqs else []


def motivo_erro(modelo, bench):
    achados = [l for l in erros.splitlines() if modelo in l and bench in l]
    return achados[-1][:300] if achados else "sem linha no CSV e sem erro registrado"


# a) OAB-Exams: 100 exemplos, f16, 3 modelos
acc = {}
for modelo in (S3, S7, S14):
    r = linha(modelo, "f16", "oab")
    if r: acc[modelo] = float(r["acuracia"])
if len(acc) == 3:
    a3, a7, a14 = acc[S3], acc[S7], acc[S14]
    ok = min(acc.values()) >= 0.35 and a3 <= a7 + 0.03 and a7 <= a14 + 0.03 and a14 >= a3 + 0.05
    out["oab"] = {"status": "ok" if ok else "pulado", "acuracias": acc,
                  "regra": "todas >= 0,35; 3B <= 7B+0,03; 7B <= 14B+0,03; 14B >= 3B+0,05 (n=100, erro padrao ~0,05)"}
    if not ok:
        out["oab"]["motivo"] = f"criterio de aceite nao atendido: 3B {a3:.2f}, 7B {a7:.2f}, 14B {a14:.2f}"
        for a in amostras(S7, "f16", "oab"):
            escolha = max(range(len(a["resps"])), key=lambda i: float(a["resps"][i][0][0]))
            relatorio.append(f"--- OAB exemplo (7B f16): prompt:\n{a['arguments']['gen_args_0']['arg_0']}\nalvo (indice): {a['target']} ; escolha do modelo (indice): {escolha}")
else:
    out["oab"] = {"status": "pulado", "motivo": "nao rodou nos 3 modelos: " + motivo_erro("Qwen2.5", "oab")}

# b) MATH-500 (minerva_math500 + math_verify), 7B q4_k_m, 20 exemplos, >= 0,3
r = linha(S7, "q4_k_m", "math500")
if r:
    v = float(r["acuracia"])
    out["math500"] = {"status": "ok" if v >= 0.3 else "pulado", "math_verify": v, "regra": ">= 0,3 em 20 exemplos"}
    if v < 0.3:
        out["math500"]["motivo"] = f"math_verify {v:.2f} < 0,30 em 20 exemplos"
        for a in amostras(S7, "q4_k_m", "math500"):
            relatorio.append(f"--- MATH-500 extracao: resposta (final): ...{str(a['resps'][0][0])[-300:]}\nfiltrada: {a['filtered_resps']}\nalvo: {a['target']}")
else:
    out["math500"] = {"status": "pulado", "motivo": motivo_erro(S7, "math500")}

# c) PubMedQA e d) WMT24++: carregam e rodam 20 exemplos
for bench in ("pubmedqa", "wmt24pp"):  # o job 892 gravou a linha como wmt24pp
    r = linha(S7, "q4_k_m", bench)
    if r and int(r["n"]) >= 20 and r["acuracia"] != "":
        out[bench] = {"status": "ok", "n": int(r["n"]), "valor": float(r["acuracia"])}
    else:
        out[bench] = {"status": "pulado", "motivo": "nao rodou 20 exemplos: " + motivo_erro(S7, bench)}

# e) codigo: so se a home NAO aparece no conteiner isolado e a geracao funcionou
iso = open(sys.argv[1]).read() if len(sys.argv) > 1 and os.path.exists(sys.argv[1]) else ""
isolado = "No such file or directory" in iso and "\ntotal " not in iso and "\ndrwx" not in iso
gen = {}
for bench in ("humaneval", "mbpp"):
    p = os.path.join(DIR, "amostras", S7, "q4_k_m", bench, "geracao.json")
    if os.path.exists(p):
        g = json.load(open(p))
        gen[bench] = g["n"] >= 5 and g["tokens_por_resposta"] > 0
if not isolado:
    out["codigo"] = {"status": "pulado", "motivo": "a home aparece no conteiner de pontuacao (ou o log de isolamento nao foi lido): codigo gerado nao sera executado"}
elif not all(gen.get(b) for b in ("humaneval", "mbpp")):
    out["codigo"] = {"status": "pulado", "motivo": "geracao de HumanEval+/MBPP+ falhou no teste: " + motivo_erro(S7, "mbpp")}
else:
    out["codigo"] = {"status": "ok", "isolamento": "home nao visivel", "geracao_teste": gen}
for b in ("humaneval", "mbpp"): out[b] = {"status": out["codigo"]["status"], "motivo": out["codigo"].get("motivo", "")}

# f) GPQA
r = linha(S7, "q4_k_m", "gpqa")
if r and int(r["n"]) >= 20: out["gpqa"] = {"status": "ok", "n": int(r["n"]), "valor": float(r["acuracia"])}
elif not os.environ.get("HF_TOKEN"): out["gpqa"] = {"status": "pulado", "motivo": "HF_TOKEN ausente no ambiente do job"}
else: out["gpqa"] = {"status": "pulado", "motivo": motivo_erro(S7, "gpqa")}

out["wmt24"] = out["wmt24pp"]  # nome do benchmark no medir.py
json.dump(out, open(os.path.join(AQUI, "etapa1.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
print("\n".join(relatorio))
