"""Pipeline completo: roda as etapas prontas em sequencia e grava um JSON por etapa.
Cada etapa nova que fechamos entra como uma funcao em ETAPAS (no fim da lista).

Uso (da raiz do repositorio):
  python pipeline.py "Quero responder duvidas de saude, tenho 16 GB" --backend gemini --modelo gemini-2.5-flash
  python pipeline.py --pedido saidas/pedido.json --memoria-gb 8      # pula a etapa 1 (sem API)
Opcoes: --memoria-gb --banda-gb-s --min-tok-s --max-perda-pct  (limites; valem mais que o pedido)
Saida: pasta --saida (padrao saidas/) com pedido.json, diagnostico.json, ...
A chave do Gemini vem de GEMINI_API_KEY (variavel de ambiente), nunca de arquivo.
"""
import argparse, json, os, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
for pasta in ("etapa1_extracao", "etapa2_diagnostico"):
    sys.path.insert(0, os.path.join(RAIZ, pasta))


def etapa1_extracao(ctx):
    if ctx["args"].pedido:                                   # pedido ja extraido: nao chama a API
        return json.load(open(ctx["args"].pedido))
    from extrair import extrair
    a = ctx["args"]
    return extrair(a.texto, a.backend, a.modelo, a.url)


def etapa2_diagnostico(ctx):
    from diagnosticar import diagnosticar
    a = ctx["args"]
    return diagnosticar(ctx["pedido"], a.memoria_gb, a.banda_gb_s, a.min_tok_s, a.max_perda_pct)


# (nome do arquivo de saida, funcao). Ordem = ordem do pipeline. Cada funcao le/escreve em ctx.
ETAPAS = [
    ("pedido", etapa1_extracao),
    ("diagnostico", etapa2_diagnostico),
]


def resumo(ctx):
    p, d = ctx["pedido"], ctx["diagnostico"]
    q, m, l = d["qualidade"], d["memoria"], d["latencia"]
    print("\n--- resumo ---")
    print(f"pedido      : tarefa={(p['tarefa'] or {}).get('valor')} dominio={(p['dominio'] or {}).get('valor')} "
          f"modelo={(p['modelo'] or {}).get('id') or (p['modelo'] or {}).get('valor')}")
    print(f"qualidade   : {q['celula_pedida']} -> {', '.join(q['benchmarks']) or '(falta medir)'} [{q['medida']}]")
    print(f"memoria     : orcamento={m['orcamento_gb']} GB ({m['origem']}), ctx={m['ctx_alvo']['valor']}")
    print(f"latencia    : banda={l['banda_gb_s']} GB/s ({l['origem']}), meta={l['meta']['min_tok_s']} tok/s")
    for av in d["avisos"]: print("aviso       :", av)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("texto", nargs="?", help="pedido em texto livre (obrigatorio se nao usar --pedido)")
    ap.add_argument("--pedido", help="JSON de pedido ja extraido: pula a etapa 1")
    ap.add_argument("--backend", default="gemini"); ap.add_argument("--modelo"); ap.add_argument("--url")
    ap.add_argument("--memoria-gb", type=float); ap.add_argument("--banda-gb-s", type=float)
    ap.add_argument("--min-tok-s", type=float); ap.add_argument("--max-perda-pct", type=float)
    ap.add_argument("--saida", default=os.path.join(RAIZ, "saidas"))
    a = ap.parse_args()
    if not a.texto and not a.pedido: ap.error("informe o texto ou --pedido")
    os.makedirs(a.saida, exist_ok=True)
    ctx = {"args": a}
    for nome, fn in ETAPAS:
        ctx[nome] = fn(ctx)
        with open(os.path.join(a.saida, nome + ".json"), "w") as f:
            json.dump(ctx[nome], f, ensure_ascii=False, indent=2)
    resumo(ctx)
    print(f"\ngravado em {a.saida}/")


if __name__ == "__main__":
    main()