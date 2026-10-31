"""Apaga os arquivos de um modelo (pesos originais + GGUFs) SO se todas as medidas pedidas ja estiverem registradas.
Uso: limpar.py MODELO --exigir mmlu medqa humaneval ... [--niveis f16 q8_0 q4_k_m]
Uma medida conta se houver a linha (modelo, nivel, prova) em resultados.csv, kv.csv ou raciocinio.csv; humaneval e mbpp contam pela geracao salva (amostras/.../geracao.json),
porque a pontuacao do evalplus so entra no CSV depois, no job isolado. Nao apaga nada fora de work/models."""
import argparse, csv, os, shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELOS = "/beegfs/home/user_muriloalves/work/models"
NOMES = {"humaneval": "humaneval_plus", "mbpp": "mbpp_plus"}

ap = argparse.ArgumentParser()
ap.add_argument("modelo")
ap.add_argument("--exigir", nargs="+", required=True)
ap.add_argument("--niveis", nargs="+", default=["f16", "q8_0", "q4_k_m"])
a = ap.parse_args()

linhas = set()
for arq in ("resultados.csv", "kv.csv", "raciocinio.csv"):
    caminho = os.path.join(AQUI, arq)
    if os.path.exists(caminho): linhas |= {(r["modelo"], r["nivel"], r["benchmark"]) for r in csv.DictReader(open(caminho))}


def feito(nivel, prova):
    if prova in NOMES:
        return os.path.exists(os.path.join(AQUI, "amostras", a.modelo, nivel, prova, "geracao.json")) or (a.modelo, nivel, NOMES[prova]) in linhas
    return (a.modelo, nivel, prova) in linhas


faltam = [(n, p) for n in a.niveis for p in a.exigir if not feito(n, p)]
if faltam:
    print(f"limpar {a.modelo}: NAO apagado, faltam {len(faltam)} medidas: {faltam[:12]}", flush=True)
    raise SystemExit(0)
alvos = [os.path.join(MODELOS, a.modelo)] + [os.path.join(MODELOS, f"{a.modelo.lower()}-{n}.gguf{sufixo}") for n in ("f16", "q8_0", "q4_k_m") for sufixo in ("", ".parcial")]  # nome exato: Qwen3-8B nao pega Qwen3-8B-Base
livre = 0
for alvo in alvos:
    if not os.path.exists(alvo) or os.path.dirname(os.path.abspath(alvo)) != MODELOS: continue
    tam = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(alvo) for f in fs) if os.path.isdir(alvo) else os.path.getsize(alvo)
    shutil.rmtree(alvo) if os.path.isdir(alvo) else os.remove(alvo)
    livre += tam
print(f"limpar {a.modelo}: todas as medidas registradas; apagados pesos e GGUFs ({livre / 1e9:.1f} GB)", flush=True)
