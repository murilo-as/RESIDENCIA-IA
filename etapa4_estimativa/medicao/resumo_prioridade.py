"""Escreve resumo_prioridade_N.md: linhas novas dos CSVs desde o inicio da prioridade N, erros, anomalias e tempos. Uso: resumo_prioridade.py N"""
import csv, datetime, glob, json, math, os, re, sys
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1])
agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ler_marco(n):
    p = os.path.join(AQUI, "logs", "blocos", f"prioridade_{n}.inicio")
    return open(p).read().strip() if os.path.exists(p) else None


inicio, fim = ler_marco(N) or "0", ler_marco(N + 1) or "9"
no_periodo = lambda ts: inicio <= ts < fim
CSVS = ["resultados.csv", "kv.csv", "raciocinio.csv", "vazao_moe.csv"]
novas = {}
for arq in CSVS:
    p = os.path.join(AQUI, arq)
    if os.path.exists(p): novas[arq] = [r for r in csv.DictReader(open(p)) if no_periodo(r["data"])]


def tabela(linhas, cols):
    return ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in linhas]


def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None


out = [f"# Prioridade {N}: resumo\n", f"Periodo: {inicio} a {fim if fim != '9' else agora} (gerado em {agora}).\n"]
out.append("## Linhas novas\n")
for arq, linhas in novas.items():
    if not linhas: continue
    cols = ["modelo", "nivel"] + (["kv", "raciocinio"] if "kv" in linhas[0] else []) + ["benchmark", "n", "acuracia", "erro_padrao", "tempo_s", "tokens_por_resposta", "cortadas"]
    out += [f"### {arq} ({len(linhas)} linhas)\n"] + tabela(linhas, cols) + [""]
if not any(novas.values()): out.append("(nenhuma linha nova)\n")

# erros do periodo (so a primeira linha de cada registro)
out.append("## Erros (erros.log)\n")
p = os.path.join(AQUI, "erros.log")
erros = [l[:400] for l in open(p) if re.match(r"\d{4}-\d\d-\d\dT", l) and no_periodo(l.split()[0])] if os.path.exists(p) else []
out.append("```\n" + ("\n".join(erros) if erros else "(nenhum erro novo)") + "\n```\n")
t5 = os.path.join(AQUI, "logs", "teste5.json")
if os.path.exists(t5):
    d = json.load(open(t5))
    rep = {k: v for k, v in d.items() if no_periodo(v["data"])}
    out.append(f"Testes de 5 exemplos no periodo: {len(rep)} ({sum(not v['ok'] for v in rep.values())} reprovados)" + "".join(f"\n- reprovado {k}: {v['motivo'][:200]}" for k, v in rep.items() if not v["ok"]) + "\n")

# anomalias
out.append("## Anomalias\n")
anom = []
for arq in ("resultados.csv", "kv.csv", "raciocinio.csv"):
    por = defaultdict(dict)
    for r in novas.get(arq, []): por[(r["modelo"], r["benchmark"], r.get("kv", ""))][r["nivel"]] = r
    for (mod, b, kv), niv in por.items():
        if "f16" in niv and "q4_k_m" in niv and b != "mmlu_completo":
            a, c = f(niv["f16"]["acuracia"]), f(niv["q4_k_m"]["acuracia"])
            se = math.hypot(f(niv["f16"]["erro_padrao"]) or 0, f(niv["q4_k_m"]["erro_padrao"]) or 0)
            if a is not None and c is not None and c - a > 2 * se: anom.append(f"{arq}: {mod} {b}: q4_k_m ({c:.4f}) acima do f16 ({a:.4f}) por mais de 2 erros padrao ({se:.4f})")
    for r in novas.get(arq, []):
        a, n, cort = f(r["acuracia"]), f(r["n"]), f(r["cortadas"])
        if a == 0: anom.append(f"{arq}: {r['modelo']} {r['nivel']} {r['benchmark']}: acuracia 0")
        if cort and n and r["benchmark"] not in ("mmlu_letra", "oab_letra") and cort / n > 0.05: anom.append(f"{arq}: {r['modelo']} {r['nivel']} {r['benchmark']}: {cort / n:.0%} das respostas cortadas")
base = {(r["modelo"], r["nivel"], r["benchmark"]): r for r in novas.get("kv.csv", []) if r["kv"] == "16"}
for r in novas.get("kv.csv", []):
    b = base.get((r["modelo"], r["nivel"], r["benchmark"]))
    if r["kv"] != "16" and b and f(r["acuracia"]) is not None:
        se = math.hypot(f(r["erro_padrao"]) or 0, f(b["erro_padrao"]) or 0)
        if f(b["acuracia"]) - f(r["acuracia"]) > 2 * se: anom.append(f"kv.csv: {r['modelo']} {r['benchmark']}: queda com kv={r['kv']} ({f(r['acuracia']):.4f} contra {f(b['acuracia']):.4f} com kv=16)")
out.append("\n".join(f"- {a}" for a in anom) if anom else "(nenhuma regra de anomalia disparou)")
out.append("")

# tempos: soma de tempo_s por prova e duracao de cada chamada do medir.py nos blocos
out.append("\n## Tempos\n")
soma = defaultdict(float)
for linhas in novas.values():
    for r in linhas: soma[r["benchmark"]] += f(r["tempo_s"]) or 0
out += ["Soma de tempo_s por prova (so o tempo medido, sem carga de modelo nem montagem das tarefas): " + ", ".join(f"{b} {t / 3600:.2f} h" for b, t in sorted(soma.items())), ""]
chamadas = []
for arq in sorted(glob.glob(os.path.join(AQUI, "logs", "blocos", "*.txt"))):
    ini = None
    for l in open(arq):
        ts = l.split()[0] if l.strip() else ""
        if " inicio medir.py " in l: ini, cmd = ts, l.split("inicio medir.py ")[1].strip()
        elif " fim rc=" in l and ini:
            if no_periodo(ini):
                dur = (datetime.datetime.fromisoformat(ts.rstrip("Z")) - datetime.datetime.fromisoformat(ini.rstrip("Z"))).total_seconds() / 3600
                chamadas.append(f"| {os.path.basename(arq)[:-4]} | {cmd[:110]} | {dur:.2f} h | {l.split('rc=')[1].strip()} |")
            ini = None
out += ["| bloco | chamada | duracao | rc |", "|---|---|---|---|"] + (chamadas or ["| - | - | - | - |"]) + [""]

# partes especificas de cada prioridade
def incluir(titulo, caminho):
    if os.path.exists(caminho): out.extend([f"## {titulo}\n", open(caminho).read().strip(), ""])


if N == 1:
    incluir("1.1 Validacao da geracao de letra", os.path.join(AQUI, "logs", "p1_1_validacao.md"))
    kvm = os.path.join(AQUI, "kv_memoria.csv")
    if os.path.exists(kvm):
        mem = [r for r in csv.DictReader(open(kvm)) if r["momento"] == "pronto" and no_periodo(r["data"])]
        for r in mem:
            u, a, g = f(r["mem_usada_mib"]), f(r["mem_antes_do_servidor_mib"]), f(r["gguf_mib"])
            r["mem_alem_do_gguf_mib"] = round(u - a - g) if None not in (u, a, g) else ""
        out += ["## 1.2 Memoria do servidor (formula da etapa 3 contra o medido)\n",
                "`mem_alem_do_gguf_mib` = memoria usada da maquina depois de subir o servidor - antes - tamanho do GGUF: inclui o KV, os buffers de calculo e o contexto; a formula cobre so o KV.\n"]
        out += tabela(mem, ["modelo", "nivel", "kv", "ctx_total", "kv_formula_mib", "gguf_mib", "mem_alem_do_gguf_mib", "pico_rss_servidor_mib", "nvidia_smi"]) + [""]
    d = [r for r in novas.get("kv.csv", []) if r["benchmark"] in ("mmlu_logprob_fp16", "mmlu_logprob_bf16", "mmlu_letra") and r["modelo"] in ("Qwen3.5-9B", "Qwen3-8B")]
    if d:
        out += ["## 1.4 Diagnostico do MMLU (mesma amostra de 1425 questoes)\n"] + tabela(sorted(d, key=lambda r: (r["modelo"], r["benchmark"], r["nivel"])), ["modelo", "nivel", "benchmark", "n", "acuracia", "erro_padrao"]) + [""]
if N == 2:
    prompts = sorted({(p.split("/amostras/")[1].split("/")[0], open(p).read().strip()) for p in glob.glob(os.path.join(AQUI, "amostras", "*", "*", "*", "*", "prompt_sistema.txt"))})
    if prompts: out += ["## Prompt de sistema usado nos especialistas de matematica\n"] + [f"- {m}: `{t}`" for m, t in prompts] + [""]
if N == 3:
    incluir("3.1 Acesso ao GPQA", os.path.join(AQUI, "logs", "p3_1_gpqa_acesso.txt"))
    incluir("3.2 Vazao dos MoE", os.path.join(AQUI, "vazao_moe.md"))
out.append("## Pendencias\n\nVer a secao de erros acima e `erros.log`; provas puladas pelo teste de 5 exemplos aparecem em `logs/teste5.json`.\n")
open(os.path.join(AQUI, f"resumo_prioridade_{N}.md"), "w").write("\n".join(out) + "\n")
print(f"resumo_prioridade_{N}.md escrito ({sum(len(v) for v in novas.values())} linhas novas)")
