"""Avalia a etapa 1 nos pedidos anotados (casos/pedidos.jsonl).

Por campo, conta: acerto | alucinacao (preencheu o que o texto nao diz) | omissao (deixou vazio o que o texto diz) | errado (valor diferente).
Compara o pedido FINAL (depois do pos-processamento), que e o que a etapa 2 recebe.

Uso: python avaliar_extracao.py --backend gabarito
     python avaliar_extracao.py --backend llamacpp --modelo llm/qwen2.5-1.5b-instruct-q4_k_m.gguf
"""
import argparse, json, os, sys, time
from collections import defaultdict
from extrair import extrair, NOMES, _norm, AQUI, _achar

CAMPOS = ["modelo", "tarefa", "dominio", "hardware", "memoria_gb", "preferencia",
          "recursos.dados", "recursos.treino", "recursos.gpu", "entrada_longa", "raciocinio", "idioma"]

def pegar(d, campo):
    for p in campo.split("."): d = d[p]
    return d

def igual(campo, pred, gold, caso, final):
    if campo == "modelo":                        # o que importa e o id resolvido
        return final["modelo"].get("id") == caso["modelo_id_esperado"]
    if campo == "hardware":                      # mencao livre: basta uma conter a outra
        return _norm(pred) in _norm(gold) or _norm(gold) in _norm(pred)
    if campo == "memoria_gb":
        return float(pred) == float(gold)
    return pred == NOMES.get(gold, gold)

def avaliar(backend, modelo=None, url=None):
    casos = [json.loads(l) for l in open(os.path.join(AQUI, "casos", "pedidos.jsonl"))]
    fichas = json.load(open(_achar("fichas.json")))["fichas"]
    cont = defaultdict(lambda: defaultdict(int)); saidas = []; t0 = time.time()
    for c in casos:
        erro = None
        try:
            final = extrair(c["texto"], backend, modelo, url, bruto=c["gabarito"] if backend == "gabarito" else None, fichas=fichas)
        except Exception as e:
            final = None; erro = f"{type(e).__name__}: {e}"[:1500]; print(f"{c['id']}: ERRO {erro}", file=sys.stderr)
        saidas.append({"id": c["id"], "final": final, **({"erro": erro} if erro else {})})
        for campo in CAMPOS:
            gold = pegar(c["gabarito"], campo)["valor"]
            if campo == "modelo": gold = c["modelo_id_esperado"]
            if final is None: cont[campo]["erro_execucao"] += 1; continue
            pred = pegar(final, campo)["valor"]
            if campo == "modelo": pred = final["modelo"].get("id") or pred     # mencao nao resolvida conta como valor (pega falso positivo)
            if gold is None and pred is None: cont[campo]["acerto"] += 1
            elif gold is None: cont[campo]["alucinacao"] += 1
            elif pred is None: cont[campo]["omissao"] += 1
            elif igual(campo, pred, gold, c, final): cont[campo]["acerto"] += 1
            else: cont[campo]["errado"] += 1
    seg = time.time() - t0
    n = len(casos); total = sum(cont[c]["acerto"] for c in CAMPOS)
    print(f"backend={backend} modelo={modelo or '-'}  casos={n}  tempo={seg:.0f}s")
    print(f"{'campo':16s} {'acerto':>7s} {'alucin.':>8s} {'omissao':>8s} {'errado':>7s}")
    for campo in CAMPOS:
        k = cont[campo]
        print(f"{campo:16s} {k['acerto']:4d}/{n:<2d} {k['alucinacao']:8d} {k['omissao']:8d} {k['errado']:7d}")
    print(f"{'TOTAL':16s} {total}/{n * len(CAMPOS)} = {total / (n * len(CAMPOS)):.0%}")
    os.makedirs(os.path.join(AQUI, "resultados"), exist_ok=True)
    nome = os.path.join(AQUI, "resultados", f"resultado_{backend}.json")
    json.dump({"backend": backend, "modelo": modelo, "tempo_s": round(seg, 1), "contagem": cont, "saidas": saidas},
              open(nome, "w"), ensure_ascii=False, indent=1)
    return cont

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--backend", default="gabarito")
    ap.add_argument("--modelo"); ap.add_argument("--url"); a = ap.parse_args()
    avaliar(a.backend, a.modelo, a.url)