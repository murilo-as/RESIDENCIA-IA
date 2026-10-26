"""Escreve resumo.md: tabela do CSV, erros.log, o que foi pulado na etapa 1 e o pareado f16 x q4_k_m de cada (modelo, benchmark)."""
import csv, json, os
from pareado import comparar, texto

AQUI = os.path.dirname(os.path.abspath(__file__))
out = ["# Resumo da medição\n"]

arq = os.path.join(AQUI, "resultados.csv")
linhas = list(csv.reader(open(arq))) if os.path.exists(arq) else []
out.append("## resultados.csv\n")
if linhas:
    out += ["| " + " | ".join(linhas[0]) + " |", "|" + "---|" * len(linhas[0])] + ["| " + " | ".join(l) + " |" for l in linhas[1:]]
else:
    out.append("(sem resultados.csv)")

out.append("\n## Pulado na etapa 1\n")
e1 = os.path.join(AQUI, "etapa1.json")
if os.path.exists(e1):
    pulados = {b: v.get("motivo", "") for b, v in json.load(open(e1)).items() if v.get("status") == "pulado"}
    out.append("\n".join(f"- **{b}**: {m}" for b, m in pulados.items()) if pulados else "(nada foi pulado)")
else:
    out.append("(sem etapa1.json)")

out.append("\n## erros.log\n")
erros = os.path.join(AQUI, "erros.log")
out.append("```\n" + (open(erros).read().strip() if os.path.exists(erros) else "(vazio)") + "\n```")

out.append("\n## Pareado f16 x q4_k_m\n")
if linhas:
    cab = linhas[0]
    pares = sorted({(r[cab.index("modelo")], r[cab.index("benchmark")]) for r in linhas[1:]})
    niveis = {(r[cab.index("modelo")], r[cab.index("benchmark")], r[cab.index("nivel")]) for r in linhas[1:]}
    for modelo, bench in pares:
        if (modelo, bench, "f16") not in niveis or (modelo, bench, "q4_k_m") not in niveis: continue
        try: out.append("```\n" + texto(comparar(AQUI, modelo, "f16", "q4_k_m", bench)) + "\n```")
        except Exception as e: out.append(f"```\n{modelo} {bench}: sem comparacao pareada ({type(e).__name__}: {str(e)[:160]})\n```")
open(os.path.join(AQUI, "resumo.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
