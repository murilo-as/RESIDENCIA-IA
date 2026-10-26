"""Etapa 4 - Análise: leave-one-out de cada modelo medido, por benchmark, com erro por tipo (interpolação ou extrapolação) e linha de base ingênua.
  python analise.py [-r resultados.csv ...] [-o analise.md]"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estimar_qualidade as Q


def tipo(metodo):
    return "extrapolacao" if "extrap" in metodo or "outra_geracao" in metodo else "interpolacao"


def fmt(x, p=1):
    return "-" if x is None else f"{x:.{p}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-r", "--resultados", nargs="+", default=Q.CSVS)
    ap.add_argument("-o", "--saida")
    a = ap.parse_args()
    F = Q.fichas()
    M, formas = Q.ler_medicoes(a.resultados, F), Q.ler_forma(F)
    L, todas = [f"# Leave-one-out ({len(M)} medidas; arquivos: {', '.join(os.path.basename(c) for c in a.resultados)})\n"], []
    for i in sorted({k[0] for k in M}):
        rows = Q.loo(F, M, i, formas)
        if not any(r["est"] is not None for r in rows):
            continue
        L += [f"## {i}\n", "| bits | benchmark | real | estimado | erro (pts) | base | erro base (pts) | ruido (pts) | metodo |", "|---:|---|---:|---:|---:|---:|---:|---:|---|"]
        for r in rows:
            L.append(f'| {r["bits"]} | {r["benchmark"]} | {r["real"]*100:.1f} | {fmt(None if r["est"] is None else r["est"]*100)} | {fmt(r["erro_pts"])} | '
                     f'{fmt(None if r["base"] is None else r["base"]*100)} | {fmt(r["erro_base_pts"])} | {fmt(r["ep_pts"])} | {r["metodo"]} |')
        L.append("")
        todas += [{**r, "alvo": i} for r in rows if r["erro_pts"] is not None]
    L += ["## Resumo por benchmark e tipo\n", "| benchmark | tipo | n | erro abs medio | erro abs max | linha de base (medio) | dentro de 2 erros padrao |", "|---|---|---:|---:|---:|---:|---:|"]
    for b in sorted({r["benchmark"] for r in todas}):
        for t in ("interpolacao", "extrapolacao"):
            c = [r for r in todas if r["benchmark"] == b and tipo(r["metodo"]) == t]
            if not c:
                continue
            cb = [abs(r["erro_base_pts"]) for r in c if r["erro_base_pts"] is not None]
            ok = sum(1 for r in c if r["ep_pts"] is not None and abs(r["erro_pts"]) <= 2 * r["ep_pts"])
            L.append(f'| {b} | {t} | {len(c)} | {sum(abs(r["erro_pts"]) for r in c)/len(c):.2f} | {max(abs(r["erro_pts"]) for r in c):.2f} | {fmt(sum(cb)/len(cb) if cb else None, 2)} | {ok}/{len(c)} |')
    txt = "\n".join(L)
    if a.saida:
        open(a.saida, "w", encoding="utf-8").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
