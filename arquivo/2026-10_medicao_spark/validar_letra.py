"""1.1: compara a geracao de letra (kv.csv, Qwen2.5-7B-Instruct f16, kv=16) com o log-prob (resultados.csv). Aceita se a diferenca for de ate 3 pontos nas duas provas.
Escreve logs/p1_1_validacao.md (usado no resumo_prioridade_1.md)."""
import csv, os

AQUI = os.path.dirname(os.path.abspath(__file__))
M, N = "Qwen2.5-7B-Instruct", "f16"


def ler(arq):
    p = os.path.join(AQUI, arq)
    return {(r["modelo"], r["nivel"], r["benchmark"]): r for r in csv.DictReader(open(p))} if os.path.exists(p) else {}


kv, res = ler("kv.csv"), ler("resultados.csv")
linhas, aceito = ["# 1.1 Validacao da geracao de letra (Qwen2.5-7B-Instruct f16)\n", "| prova | log-prob | letra | diferenca (pontos) | respostas sem letra | veredito |", "|---|---|---|---|---|---|"], True
for letra, logp in (("mmlu_letra", "mmlu"), ("oab_letra", "oab")):
    a, b = kv.get((M, N, letra)), res.get((M, N, logp))
    if not a or not b:
        linhas.append(f"| {letra} | {b['acuracia'] if b else '-'} | {a['acuracia'] if a else '-'} | - | - | nao medido |")
        aceito = False
        continue
    d = (float(a["acuracia"]) - float(b["acuracia"])) * 100
    ok = abs(d) <= 3.0
    aceito &= ok
    linhas.append(f"| {letra} (n={a['n']}) | {float(b['acuracia']):.4f} (n={b['n']}) | {float(a['acuracia']):.4f} | {d:+.1f} | {a['cortadas']} | {'aceito' if ok else 'REPROVADO'} |")
linhas.append(f"\n**Resultado: {'aceito, a geracao de letra pode substituir o log-prob nos experimentos de KV.' if aceito else 'reprovado (diferenca acima de 3 pontos ou prova nao medida).'}**")
if not aceito:
    linhas.append("""
Alternativa proposta (uma so): `llama-perplexity` em modo de multipla escolha (`--multiple-choice`, com o conjunto no formato HellaSwag/MC do llama.cpp), que compara a verossimilhanca das alternativas
dentro do proprio motor do llama.cpp, com o KV quantizado, sem depender de o modelo escrever a letra. Exige converter MMLU e OAB para o formato do llama-perplexity (nao feito).
Os numeros de mmlu_letra e oab_letra continuam gravados em kv.csv e servem como comparacao relativa entre tipos de KV, com a ressalva acima.""")
open(os.path.join(AQUI, "logs", "p1_1_validacao.md"), "w").write("\n".join(linhas) + "\n")
print("\n".join(linhas))
