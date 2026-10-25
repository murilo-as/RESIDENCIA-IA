"""Escreve resumo.md: tabela do CSV, erros.log e o pareado f16 x q4_k_m de cada modelo."""
import csv, os, sys
from pareado import comparar, texto

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELOS = ["Qwen2.5-3B-Instruct", "Qwen2.5-7B-Instruct", "Qwen2.5-14B-Instruct"]
out = ["# Resumo da medição (fase A)\n"]

arq = os.path.join(AQUI, "resultados.csv")
out.append("## resultados.csv\n")
if os.path.exists(arq):
    linhas = list(csv.reader(open(arq)))
    out += ["| " + " | ".join(linhas[0]) + " |", "|" + "---|" * len(linhas[0])] + ["| " + " | ".join(l) + " |" for l in linhas[1:]]
else:
    out.append("(sem resultados.csv)")

out.append("\n## erros.log\n")
erros = os.path.join(AQUI, "erros.log")
out.append("```\n" + (open(erros).read().strip() if os.path.exists(erros) else "(vazio)") + "\n```")

out.append("\n## Pareado f16 x q4_k_m\n")
for modelo in MODELOS:
    for bench in ("mmlu", "gsm8k", "gsm8k_strict"):
        try: out.append("```\n" + texto(comparar(AQUI, modelo, "f16", "q4_k_m", bench)) + "\n```")
        except Exception as e: out.append(f"```\n{modelo} {bench}: sem comparacao ({type(e).__name__}: {str(e)[:200]})\n```")
open(os.path.join(AQUI, "resumo.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
