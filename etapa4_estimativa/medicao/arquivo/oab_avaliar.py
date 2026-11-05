"""Aceite do OAB corrigido (instrucao + 5-shot, 100 questoes sorteadas, f16): >= 0,35 no 7B e 14B acima do 3B. Atualiza a chave 'oab' de etapa1.json."""
import csv, glob, json, os

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(AQUI, "etapa1_oab")
S3, S7, S14 = "Qwen2.5-3B-Instruct", "Qwen2.5-7B-Instruct", "Qwen2.5-14B-Instruct"
arq = os.path.join(DIR, "resultados.csv")
linhas = list(csv.DictReader(open(arq))) if os.path.exists(arq) else []
acc = {r["modelo"]: float(r["acuracia"]) for r in linhas if r["benchmark"] == "oab" and r["nivel"] == "f16"}
e1_arq = os.path.join(AQUI, "etapa1.json")
e1 = json.load(open(e1_arq)) if os.path.exists(e1_arq) else {}
antes = e1.get("oab", {})
if len(acc) == 3:
    ok = acc[S7] >= 0.35 and acc[S14] > acc[S3]
    e1["oab"] = {"status": "ok" if ok else "pulado", "acuracias_5shot": acc, "regra": "7B >= 0,35 e 14B > 3B (100 questoes sorteadas, seed 42, f16, instrucao + 5-shot)",
                 "antes_0shot": antes.get("acuracias_0shot") or antes.get("motivo")}
    if not ok: e1["oab"]["motivo"] = f"criterio nao atendido: 3B {acc[S3]:.2f}, 7B {acc[S7]:.2f}, 14B {acc[S14]:.2f}"
else:
    e1["oab"] = {"status": "pulado", "motivo": f"o ajuste nao rodou nos 3 modelos (acuracias obtidas: {acc})", "antes_0shot": antes.get("acuracias_0shot") or antes.get("motivo")}
json.dump(e1, open(e1_arq, "w"), indent=1, ensure_ascii=False)
print(json.dumps(e1["oab"], indent=1, ensure_ascii=False))
if e1["oab"]["status"] == "pulado":
    for f in sorted(glob.glob(os.path.join(DIR, "amostras", S7, "f16", "oab", "**", "samples_*.jsonl"), recursive=True))[-1:]:
        for linha in list(open(f))[:3]:
            a = json.loads(linha)
            escolha = max(range(len(a["resps"])), key=lambda i: float(a["resps"][i][0][0]))
            print(f"--- exemplo (7B f16): prompt:\n{a['arguments']['gen_args_0']['arg_0']}\nalvo (indice): {a['target']} ; escolha do modelo (indice): {escolha}")
