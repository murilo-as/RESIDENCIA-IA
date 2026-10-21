"""Roda as etapas em sequência e grava um JSON por etapa em saidas/.
  python pipeline.py "texto do pedido"
  python pipeline.py --pedido saidas/pedido.json    # pula a etapa 1 (sem API)
Opções (LLM, limites, saída) ficam em config.yaml; a chave do Gemini, em .env."""
import argparse, json, os, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from config import carregar as carregar_config
for pasta in ("etapa1_extracao", "etapa2_diagnostico", "etapa3_candidatura", "etapa4_estimativa"):
    sys.path.insert(0, os.path.join(RAIZ, pasta))


def etapa1_extracao(ctx):
    if ctx["args"].pedido:
        return json.load(open(ctx["args"].pedido))
    from extrair import extrair
    a, L = ctx["args"], ctx["config"]["llm"]
    return extrair(a.texto, L["backend"], L["modelo"], L["url"])


def etapa2_diagnostico(ctx):
    from diagnosticar import diagnosticar
    L = ctx["config"]["limites"]
    return diagnosticar(ctx["pedido"], L["memoria_gb"], L["banda_gb_s"], L["min_tok_s"])


def etapa3_candidatura(ctx):
    from candidatar import candidatar
    return candidatar(ctx["diagnostico"])


def etapa4_estimativa(ctx):
    from estimar import estimar
    return estimar(ctx["candidatos"], ctx["diagnostico"])


# (arquivo de saída, função). Etapa nova = uma função no fim da lista.
ETAPAS = [
    ("pedido", etapa1_extracao),
    ("diagnostico", etapa2_diagnostico),
    ("candidatos", etapa3_candidatura),
    ("estimativas", etapa4_estimativa),
]


def resumo(ctx):
    p, d = ctx["pedido"], ctx["diagnostico"]
    q, m, l = d["qualidade"], d["memoria"], d["latencia"]
    print("\n--- resumo ---")
    print(f"pedido      : tarefa={(p['tarefa'] or {}).get('valor')} dominio={(p['dominio'] or {}).get('valor')} "
          f"modelo={(p['modelo'] or {}).get('id') or (p['modelo'] or {}).get('valor')}")
    print(f"qualidade   : {q['celula_pedida']} -> {', '.join(q['benchmarks']) or '(falta medir)'} [{q['medida']}]")
    print(f"memoria     : orcamento={m['orcamento_gb']} GB ({m['origem']}), ctx={m['ctx_alvo']['valor']}")
    print(f"latencia    : banda={l['banda_gb_s']} GB/s ({l['origem']}; escala do decode vs Spark = {l['escala_decode']}), meta={l['meta']['min_tok_s']} tok/s")
    for av in d["avisos"]: print("aviso       :", av)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("texto", nargs="?", help="pedido em texto livre (obrigatorio se nao usar --pedido)")
    ap.add_argument("--pedido", help="JSON de pedido ja extraido: pula a etapa 1")
    ap.add_argument("--config", help="outro arquivo de configuracao (padrao: config.yaml na raiz)")
    a = ap.parse_args()
    cfg = carregar_config(a.config, RAIZ); a.saida = os.path.join(RAIZ, cfg["saida"])
    if not a.texto and not a.pedido: ap.error("informe o texto ou --pedido")
    os.makedirs(a.saida, exist_ok=True)
    ctx = {"args": a, "config": cfg}
    for nome, fn in ETAPAS:
        ctx[nome] = fn(ctx)
        with open(os.path.join(a.saida, nome + ".json"), "w") as f:
            json.dump(ctx[nome], f, ensure_ascii=False, indent=2)
    resumo(ctx)
    c = ctx["candidatos"]["resumo"]
    print(f"candidatura : {c['modelos_considerados']} modelos, {c['modelos_com_configuracao']} com configuracao, {c['configuracoes']} configuracoes"
          + (" (orcamento desconhecido: nada excluido por memoria)" if c["orcamento_desconhecido"] else ""))
    e = ctx["estimativas"]["resumo"]
    print(f"estimativa  : {e['com_qualidade']}/{e['configuracoes']} com qualidade medida; meta de tok/s: {e['atende_meta']}")
    print(f"\ngravado em {a.saida}/")


if __name__ == "__main__":
    main()
