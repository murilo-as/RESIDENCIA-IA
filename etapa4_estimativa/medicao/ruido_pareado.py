"""Ruido dos benchmarks: erro padrao da nota (binomial) contra erro padrao da diferenca pareada f16 x q4_k_m (mesmas questoes), para todos os modelos de amostras/.
Escreve logs/ruido_pareado.md e diagnostica o MBPP+ do Qwen2.5-3B-Instruct (so le; nao altera resultados). Uso: ruido_pareado.py [--saida logs/ruido_pareado.md]"""
import argparse, json, math, os, statistics
from pareado import comparar, carregar, AQUI

PROVAS = ["mmlu", "medqa", "oab", "pubmedqa", "gsm8k", "math500", "humaneval_plus", "mbpp_plus"]
A, B = "f16", "q4_k_m"


def modelos():
    raiz = os.path.join(AQUI, "amostras")
    return sorted(m for m in os.listdir(raiz) if all(os.path.isdir(os.path.join(raiz, m, n)) for n in (A, B)))


def linhas_ruido():
    out, falhas = [], []
    for m in modelos():
        for p in PROVAS:
            try:
                r = comparar(AQUI, m, A, B, p)
            except Exception as e:
                falhas.append((m, p, str(e)[:120])); continue
            n, pa = r["n"], r["acc_A"]
            r["ep_nota"] = math.sqrt(pa * (1 - pa) / n)
            r["z"] = r["diferenca"] / r["erro_padrao_diferenca"] if r["erro_padrao_diferenca"] else float("nan")
            out.append(r)
    return out, falhas


def pts(x): return f"{100 * x:.1f}"


def tabela(rs):
    s = ["| modelo | prova | n | f16 | q4_k_m | dif (pts) | EP da nota (pts) | EP da dif. pareada (pts) | dif/EP pareado |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rs:
        s.append(f"| {r['modelo']} | {r['benchmark']} | {r['n']} | {pts(r['acc_A'])} | {pts(r['acc_B'])} | {100 * r['diferenca']:+.1f} | {pts(r['ep_nota'])} | {pts(r['erro_padrao_diferenca'])} | {r['z']:+.1f} |")
    return s


def resumo(rs):
    s = ["| prova | modelos | EP da nota, mediana (pts) | EP da dif. pareada, mediana (pts) | razao pareado/nota | \\|dif\\| mediana (pts) | modelos com \\|dif/EP\\| > 2 |", "|---|---|---|---|---|---|---|"]
    for p in PROVAS:
        x = [r for r in rs if r["benchmark"] == p]
        if not x: continue
        ep, epp = statistics.median(r["ep_nota"] for r in x), statistics.median(r["erro_padrao_diferenca"] for r in x)
        s.append(f"| {p} | {len(x)} | {pts(ep)} | {pts(epp)} | {epp / ep:.2f} | {pts(statistics.median(abs(r['diferenca']) for r in x))} | {sum(abs(r['z']) > 2 for r in x)} |")
    return s


def diag_mbpp(modelo="Qwen2.5-3B-Instruct"):
    """Compara f16, q8_0 e q4_k_m no MBPP+: o que o job de pontuacao registrou por questao (base, plus), respostas cortadas e tokens. O codigo gerado nao fica guardado em amostras/."""
    s = [f"## Diagnostico: MBPP+ do {modelo}", ""]
    dados = {}
    for n in ("f16", "q8_0", "q4_k_m"):
        d = os.path.join(AQUI, "amostras", modelo, n, "mbpp")
        try:
            pont, ger = json.load(open(os.path.join(d, "pontuacao.json"))), json.load(open(os.path.join(d, "geracao.json")))
        except FileNotFoundError:
            continue
        dados[n] = (pont, ger)
    s += ["| nivel | n | base | plus | base=0 (nem o teste simples passa) | base ok e plus falha | cortadas | tokens/resposta |", "|---|---|---|---|---|---|---|---|"]
    for n, (p, g) in dados.items():
        t = p["tarefas"].values()
        s.append(f"| {n} | {p['n']} | {p['base']:.0f} | {p['plus']:.0f} | {sum(v[0] == 0 for v in t)} | {sum(v[0] == 1 and v[1] == 0 for v in t)} | {g['cortadas']} | {g['tokens_por_resposta']:.0f} |")
    s += ["", "Pareado por questao (mbpp_plus):", "", "| A | B | n | acc A | acc B | dif (pts) | so A acertou | so B acertou | EP da dif. (pts) | dif/EP |", "|---|---|---|---|---|---|---|---|---|---|"]
    for a, b in (("f16", "q4_k_m"), ("f16", "q8_0"), ("q8_0", "q4_k_m")):
        if a in dados and b in dados:
            r = comparar(AQUI, modelo, a, b, "mbpp_plus")
            s.append(f"| {a} | {b} | {r['n']} | {pts(r['acc_A'])} | {pts(r['acc_B'])} | {100 * r['diferenca']:+.1f} | {r['so_A_acertou']} | {r['so_B_acertou']} | {pts(r['erro_padrao_diferenca'])} | {r['diferenca'] / r['erro_padrao_diferenca']:+.1f} |")
    # questoes em que os niveis divergem: a mesma questao ora passa, ora falha (ruido de geracao) ou falha sempre (questao dificil)
    if len(dados) == 3:
        chaves = list(dados["f16"][0]["tarefas"])
        p = {n: {k: v[1] for k, v in dados[n][0]["tarefas"].items()} for n in dados}
        todas, nenhuma = sum(all(p[n].get(k) == 1 for n in p) for k in chaves), sum(all(p[n].get(k) == 0 for n in p) for k in chaves)
        s += ["", f"Das {len(chaves)} questoes, {todas} passam nos 3 niveis, {nenhuma} falham nos 3 e {len(chaves) - todas - nenhuma} divergem entre niveis."]
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=os.path.join(AQUI, "logs", "ruido_pareado.md"))
    a = ap.parse_args()
    rs, falhas = linhas_ruido()
    md = ["# Ruido dos benchmarks: erro padrao da nota x erro padrao da diferenca pareada (f16 x q4_k_m)", "",
          "EP da nota = raiz(p(1-p)/n) nas questoes comuns. EP da diferenca pareada = raiz((b + c - (b - c)^2 / n) / n^2), com b e c as questoes em que so um dos niveis acertou (mesmas questoes nos dois niveis). Dif = f16 - q4_k_m.", "",
          "## Resumo por prova", ""] + resumo(rs) + ["", "## Todos os modelos", ""] + tabela(rs)
    if falhas: md += ["", "## Sem comparacao", ""] + [f"- {m} {p}: {e}" for m, p, e in falhas]
    md += [""] + diag_mbpp()
    os.makedirs(os.path.dirname(a.saida), exist_ok=True)
    open(a.saida, "w").write("\n".join(md) + "\n")
    print(f"{a.saida}: {len(rs)} comparacoes, {len(falhas)} sem comparacao")
