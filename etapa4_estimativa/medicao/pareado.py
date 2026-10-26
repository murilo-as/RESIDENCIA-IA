"""Compara dois niveis questao a questao. Uso: pareado.py <modelo> <nivelA> <nivelB> <benchmark> [--dir DIR]
Benchmarks: mmlu, mmlu_completo, medqa, oab, pubmedqa, gpqa, gsm8k, gsm8k_strict, math500, math500_strict, humaneval_plus/base, mbpp_plus/base."""
import argparse, glob, json, math, os, re

AQUI = os.path.dirname(os.path.abspath(__file__))
# benchmark -> (pasta em amostras/, metrica por questao, filtro do lm-eval)
LM_EVAL = {"mmlu": ("mmlu", "acc", None), "mmlu_completo": ("mmlu_completo", "acc", None), "medqa": ("medqa", "acc", None), "oab": ("oab", "acc", None),
           "pubmedqa": ("pubmedqa", "acc", None), "gpqa": ("gpqa", "acc", None), "gsm8k": ("gsm8k", "exact_match", "flexible-extract"),
           "gsm8k_strict": ("gsm8k", "exact_match", "strict-match"), "math500": ("math500", "math_verify", None), "math500_strict": ("math500", "exact_match", None)}
CODIGO = {"humaneval_plus": ("humaneval", 1), "humaneval_base": ("humaneval", 0), "mbpp_plus": ("mbpp", 1), "mbpp_base": ("mbpp", 0)}


def carregar(pasta, modelo, nivel, bench):
    if bench in CODIGO:
        d, i = CODIGO[bench]
        arq = os.path.join(pasta, "amostras", modelo, nivel, d, "pontuacao.json")
        if not os.path.exists(arq): raise FileNotFoundError(f"sem {arq}")
        return {("", t): float(v[i]) for t, v in json.load(open(arq))["tarefas"].items()}
    if bench not in LM_EVAL: raise KeyError(f"sem comparacao pareada para '{bench}' (metrica de corpus ou nao suportada)")
    sub, metrica, filtro = LM_EVAL[bench]
    raiz = os.path.join(pasta, "amostras", modelo, nivel, sub)
    ultimo = {}
    for f in glob.glob(os.path.join(raiz, "**", "samples_*.jsonl"), recursive=True):
        task, ts = re.match(r"samples_(.+?)_(\d{4}-.*)\.jsonl$", os.path.basename(f)).groups()
        if task not in ultimo or ts > ultimo[task][0]: ultimo[task] = (ts, f)
    if not ultimo: raise FileNotFoundError(f"sem amostras em {raiz}")
    res = {}
    for task, (_, f) in ultimo.items():
        for linha in open(f):
            d = json.loads(linha)
            if filtro and d.get("filter") != filtro: continue
            v = d.get(metrica)
            if v is None and isinstance(d.get("metrics"), dict): v = d["metrics"].get(metrica)
            if v is None: raise KeyError(f"{f}: sem '{metrica}' (chaves: {sorted(d)})")
            res[(task, d["doc_id"])] = float(v)
    return res


def comparar(pasta, modelo, a, b, bench):
    ra, rb = carregar(pasta, modelo, a, bench), carregar(pasta, modelo, b, bench)
    comuns = sorted(set(ra) & set(rb))
    n = len(comuns)
    sa = sum(ra[k] > rb[k] for k in comuns)
    sb = sum(rb[k] > ra[k] for k in comuns)
    acc_a, acc_b = sum(ra[k] for k in comuns) / n, sum(rb[k] for k in comuns) / n
    var = (sa + sb - (sa - sb) ** 2 / n) / n ** 2
    return {"modelo": modelo, "benchmark": bench, "A": a, "B": b, "n": n, "so_em_A_ou_B": (len(ra), len(rb)), "acc_A": acc_a, "acc_B": acc_b,
            "diferenca": acc_a - acc_b, "so_A_acertou": sa, "so_B_acertou": sb, "erro_padrao_diferenca": math.sqrt(max(var, 0))}


def texto(r):
    return (f"{r['modelo']} {r['benchmark']}: n={r['n']} (amostras A/B: {r['so_em_A_ou_B'][0]}/{r['so_em_A_ou_B'][1]})\n"
            f"  acc {r['A']} = {r['acc_A']:.4f}; acc {r['B']} = {r['acc_B']:.4f}; diferenca (A-B) = {r['diferenca']:+.4f}\n"
            f"  so {r['A']} acertou: {r['so_A_acertou']}; so {r['B']} acertou: {r['so_B_acertou']}\n"
            f"  erro padrao da diferenca pareada: {r['erro_padrao_diferenca']:.4f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modelo"); ap.add_argument("nivel_a"); ap.add_argument("nivel_b"); ap.add_argument("benchmark")
    ap.add_argument("--dir", default=AQUI)
    a = ap.parse_args()
    print(texto(comparar(a.dir, a.modelo, a.nivel_a, a.nivel_b, a.benchmark)))
