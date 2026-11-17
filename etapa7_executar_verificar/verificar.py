"""Etapas 7 e 8 (rodar e verificar/atualizar), para tarefas de código: baixa o GGUF do caso, roda HumanEval+ e MBPP+ completos e a velocidade, compara com o que a
pipeline estimou e acrescenta o resultado à base (data/medicoes/verificacoes.csv e velocidade.csv, que o estimador lê quando config.yaml tem `fontes_medida: [..., verificacao]`).
  python etapa7_executar_verificar/verificar.py casos_teste/c4_traducao_12gb.json     # QUALQUER caso da pipeline (sem codigo): roda as etapas 1-6, mede a configuracao recomendada e acrescenta à base
  python etapa7_executar_verificar/verificar.py etapa7_executar_verificar/casos/c8_coder15b.json --llama-dir /caminho/llama.cpp/build/bin      # roda tudo e acrescenta à base
  python ... --limite 10 --pular-velocidade        # teste rápido do caminho (nunca entra na base)
  python ... --sem-ingerir                         # roda e só guarda o resultado
  python ... --so-ingerir resultados/<modelo>/<pasta>/resultado.json [--dry-run]     # acrescenta à base um resultado já medido
Cada caso é um JSON em etapa7_executar_verificar/casos/ (modelo, GGUF, nível, KV e o que a pipeline estimou). Os resultados ficam em resultados/<modelo>/<data>_verificacao_<nível>_kv<kv>/
e o GGUF baixado em modelos/. Linhas repetidas (mesmo modelo, nível, KV, prova e data) não são duplicadas na base.
Requisitos: llama.cpp compilado com CUDA, e  pip install huggingface_hub datasets evalplus
ATENÇÃO: o evalplus executa o código gerado pelo modelo. Rode em ambiente descartável (container/VM) se puder."""
import argparse, csv, glob, json, math, os, platform, re, shutil, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDICOES = os.path.join(RAIZ, "data", "medicoes")
BANDA_4090_GB_S = 1008                                              # especificação da RTX 4090 (mude com --banda em outra GPU)
KV_TIPO = {"16": "f16", "8": "q8_0", "4": "q4_0"}
CASO = {}                                                           # preenchido em main() com o JSON de casos/
PORTA, CTX, NP, MAX_TOKENS = 8089, 32768, 8, 1024                   # mesmo protocolo da medição do Spark (medir.py / codigo.py)
DATASETS = {"humaneval": "evalplus/humanevalplus", "mbpp": "evalplus/mbppplus"}
NOMES = {"humaneval": "HumanEval+", "mbpp": "MBPP+"}
CHAVE = {"HumanEval+": "humaneval_plus", "MBPP+": "mbpp_plus"}


def prompt(bench, d):
    if bench == "humaneval":
        return "Complete the following Python function. Reply with the complete function in one ```python code block.\n\n```python\n" + d["prompt"] + "```"
    return d["prompt"] + "\nYour code should pass these tests:\n" + "\n".join(d["test_list"][:3]) + "\nReply with the complete code in one ```python code block."


def task_id(bench, d): return d["task_id"] if bench == "humaneval" else "Mbpp/" + str(d["task_id"])


def extrair_codigo(texto):
    blocos = re.findall(r"```(?:python)?\n(.*?)```", texto, re.S)
    return max(blocos, key=len) if blocos else texto


def conversar(msg):
    corpo = {"model": "qwen", "messages": [{"role": "user", "content": msg}], "temperature": 0, "max_tokens": MAX_TOKENS}
    req = urllib.request.Request(f"http://127.0.0.1:{PORTA}/v1/chat/completions", data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=1800))
    return r["choices"][0]["message"]["content"] or "", r["usage"]["completion_tokens"]


def um(bench, d):
    texto, ntok = conversar(prompt(bench, d))
    sol = extrair_codigo(texto)
    if bench == "humaneval" and f"def {d['entry_point']}" not in sol: sol = d["prompt"] + sol
    return {"task_id": task_id(bench, d), "solution": sol, "tokens": ntok}


def _gpu():
    try: return subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip().splitlines()[0]
    except Exception: return None


def binario(llama_dir, nome):
    p = next((c for c in (os.path.join(llama_dir, nome), os.path.join(llama_dir, nome + ".exe")) if os.path.exists(c)), None) if llama_dir else shutil.which(nome)      # .exe no Windows
    if not p: sys.exit(f"não achei {nome}: use --llama-dir com a pasta onde o llama.cpp foi compilado (build/bin)")
    return p


def baixar():
    from huggingface_hub import hf_hub_download
    return hf_hub_download(CASO["gguf_repo"], CASO["gguf_arquivo"], local_dir=os.path.join(RAIZ, "modelos"))


def pasta_padrao():
    """resultados/<modelo>/<data>_verificacao_<nível>_kv<kv>; se já existe uma desta configuração, usa a mais recente (assim --pular-* não perde o que já foi medido)."""
    base = os.path.join(RAIZ, "resultados", CASO["modelo"]); sufixo = f"verificacao_{CASO['nivel']}_kv{CASO['kv']}"
    antigas = sorted(glob.glob(os.path.join(base, f"*_{sufixo}")))
    return antigas[-1] if antigas else os.path.join(base, f"{time.strftime('%Y-%m-%d')}_{sufixo}")


def velocidade(llama_dir, gguf):
    """llama-bench: geração de 128 tokens com KV q8_0 e flash attention (a configuração recomendada)."""
    cmd = [binario(llama_dir, "llama-bench"), "-m", gguf, "-ngl", "99", "-p", "512", "-n", "128", "-ctk", KV_TIPO[CASO["kv"]], "-ctv", KV_TIPO[CASO["kv"]], "-fa", "1", "-r", "5", "-o", "json"]
    saida = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    linhas = json.loads(saida[saida.index("["):])
    tg = next(l for l in linhas if l.get("n_gen", 0) > 0)
    return {"tg128_tok_s": tg["avg_ts"], "desvio": tg.get("stddev_ts")}


def gerar(llama_dir, gguf, limite):
    from datasets import load_dataset
    cmd = [binario(llama_dir, "llama-server"), "-m", gguf, "-ngl", "99", "-np", str(NP), "-c", str(CTX), "--host", "127.0.0.1", "--port", str(PORTA),
           "-ctk", KV_TIPO[CASO["kv"]], "-ctv", KV_TIPO[CASO["kv"]], "-fa", "on"]
    srv = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        for _ in range(180):
            if srv.poll() is not None: sys.exit("llama-server saiu antes de ficar pronto (confira a versão do llama.cpp e a flag -fa)")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/health", timeout=2); break
            except Exception: time.sleep(1)
        else: sys.exit("llama-server não ficou pronto em 3 minutos")
        saidas = {}
        for bench in DATASETS:
            problemas = list(load_dataset(DATASETS[bench])["test"])
            if limite: problemas = problemas[:limite]
            t0 = time.perf_counter()
            with ThreadPoolExecutor(NP) as ex: saidas[bench] = list(ex.map(lambda d: um(bench, d), problemas))
            print(f"{NOMES[bench]}: {len(problemas)} soluções geradas em {time.perf_counter() - t0:.0f}s", flush=True)
        return saidas
    finally:
        srv.terminate(); srv.wait(timeout=30)


def pontuar(bench, solucoes, pasta):
    """Nota 'plus' do evalplus (passa nos testes base e nos extras), como nas medições do projeto. Problemas não gerados contam como erro."""
    import evalplus.data as ed
    todos = list(ed.get_human_eval_plus() if bench == "humaneval" else ed.get_mbpp_plus())
    gerados = {s["task_id"] for s in solucoes}
    amostras = os.path.join(pasta, f"{bench}.jsonl")
    with open(amostras, "w") as f:
        for s in solucoes: f.write(json.dumps({"task_id": s["task_id"], "solution": s["solution"]}) + "\n")
        for t in todos:
            if t not in gerados: f.write(json.dumps({"task_id": t, "solution": "pass"}) + "\n")
    antigo = os.path.join(pasta, f"{bench}_eval_results.json")
    if os.path.exists(antigo): os.remove(antigo)             # o evalplus reaproveita o resultado de uma rodada anterior (ex.: teste rápido) e não pontua de novo
    subprocess.run([sys.executable, "-m", "evalplus.evaluate", "--dataset", bench, "--samples", amostras], check=True)
    res = json.load(open(antigo))["eval"]
    assert len(res) == len(todos), f"{bench}: o evalplus avaliou {len(res)} problemas, esperava {len(todos)}"
    ok = sum(res[s["task_id"]][0]["base_status"] == "pass" and res[s["task_id"]][0]["plus_status"] == "pass" for s in solucoes)
    return ok, len(solucoes)


def veredito(medido, est):
    return "DENTRO da faixa" if abs(medido - est["nota"]) <= est["meio"] else "FORA da faixa"


CAMPOS_V = ["modelo", "nivel", "kv", "raciocinio", "benchmark", "n", "acuracia", "erro_padrao", "tokens_por_resposta", "estimado", "meio_estimado", "caso", "maquina", "gpu", "llama_cpp", "gguf", "data"]
CAMPOS_S = ["modelo", "nivel", "kv", "gpu", "banda_gb_s", "tg_tok_s", "desvio", "bytes_gib", "eficiencia", "maquina", "llama_cpp", "caso", "data"]
PROVAS = {"HumanEval+": "humaneval_plus", "MBPP+": "mbpp_plus"}


def acrescentar(arq, campos, linhas, chave, dry):
    existe = [dict(l) for l in csv.DictReader(open(arq, encoding="utf-8"))] if os.path.exists(arq) else []
    ja = {tuple(l[c] for c in chave) for l in existe}
    novas = [l for l in linhas if tuple(str(l[c]) for c in chave) not in ja]
    if novas and not dry:
        novo = not os.path.exists(arq)
        with open(arq, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, campos)
            if novo: w.writeheader()
            w.writerows(novas)
    print(f"{os.path.basename(arq)}: {len(novas)} linha(s) {'a gravar' if dry else 'gravada(s)'}, {len(linhas) - len(novas)} já existia(m)")


def ingerir(r, dry_run=False):
    """Etapa 8: acrescenta o resultado à base da pipeline (verificacoes.csv: nota por prova; velocidade.csv: tok/s e eficiência da banda)."""
    if r.get("limite"): raise SystemExit("resultado de teste rápido (--limite): não entra na base")
    c = r["config"]
    comum = {"maquina": r.get("maquina"), "gpu": r.get("gpu"), "llama_cpp": " ".join(r.get("llama_cpp") or []), "caso": c["caso"], "data": r["data"]}
    cod, vel = [], []
    for nome, m in (r.get("codigo") or {}).items():
        if nome not in PROVAS: continue
        b = PROVAS[nome]; e = (r.get("estimado") or {}).get(b, {})
        cod.append({"modelo": c["modelo"], "nivel": c["nivel"], "kv": c["kv"], "raciocinio": c["raciocinio"], "benchmark": b, "n": m["n"], "acuracia": round(m["passou"] / m["n"], 6),
                    "erro_padrao": round(m["erro_padrao_pts"] / 100, 6), "tokens_por_resposta": m["tokens_medios"], "estimado": e.get("nota"), "meio_estimado": e.get("meio"),
                    "gguf": r["modelo"], **comum})
    for p in r.get("provas") or []:
        cod.append({"modelo": c["modelo"], "nivel": c["nivel"], "kv": c["kv"], "raciocinio": c["raciocinio"], "benchmark": p["base"], "n": p["n"], "acuracia": p["acuracia"],
                    "erro_padrao": p["erro_padrao"], "tokens_por_resposta": p["tokens"], "estimado": p["estimado"], "meio_estimado": p["meio"], "gguf": r["modelo"], **comum})
    if r.get("velocidade"):
        v = r["velocidade"]
        vel.append({"modelo": c["modelo"], "nivel": c["nivel"], "kv": c["kv"], "gpu": r.get("gpu"), "banda_gb_s": r["banda_gb_s"], "tg_tok_s": round(v["tg128_tok_s"], 1),
                    "desvio": round(v.get("desvio") or 0, 1), "bytes_gib": r["bytes_gib"], "eficiencia": v["eficiencia_medida"], **{k: comum[k] for k in ("maquina", "llama_cpp", "caso", "data")}})
    acrescentar(os.path.join(MEDICOES, "verificacoes.csv"), CAMPOS_V, cod, ("modelo", "nivel", "kv", "benchmark", "data"), dry_run)
    acrescentar(os.path.join(MEDICOES, "velocidade.csv"), CAMPOS_S, vel, ("modelo", "nivel", "kv", "gpu", "data"), dry_run)
    for l in cod:
        d = l["acuracia"] * 100 - (l["estimado"] or 0); dentro = l["estimado"] is not None and abs(d) <= l["meio_estimado"]
        print(f"  {l['benchmark']}: estimado {l['estimado']} ± {l['meio_estimado']} | medido {l['acuracia'] * 100:.1f} | {'dentro' if dentro else 'FORA'} da faixa")


# rotulo da prova na pipeline -> (benchmark do medir.py, nome na base). MedQA/PubMedQA/MMLU ainda nao: usam log-prob pelo hf, nao so o llama-server
GENERICAS = {"GSM8K": ("gsm8k", "gsm8k"), "MATH-500": ("math500", "math500"), "WMT24++": ("wmt24", "wmt24"), "OAB-Exams 1a fase": ("oab_letra", "oab")}
NIVEL_PESOS = {"16": "f16", "8": "q8_0", "4": "q4_k_m"}


def rodar_generico(a):
    """Caso da pipeline (casos_teste/cN.json): etapas 1-6 -> configuração recomendada -> mede com o protocolo da Spark (medir.py) -> compara -> base."""
    import yaml
    sys.path.insert(0, os.path.join(RAIZ, "etapa4_estimativa", "medicao"))
    import medir
    caso = os.path.abspath(a.caso); yml = os.path.splitext(caso)[0] + ".yaml"
    config = yml if os.path.exists(yml) else os.path.join(RAIZ, "config.yaml")
    subprocess.run([sys.executable, os.path.join(RAIZ, "pipeline.py"), "--pedido", caso] + (["--config", yml] if config == yml else []), check=True, cwd=RAIZ)
    saida = os.path.join(RAIZ, yaml.safe_load(open(config, encoding="utf-8"))["saida"])
    rec = json.load(open(os.path.join(saida, "recomendacao.json"), encoding="utf-8")); est = json.load(open(os.path.join(saida, "estimativas.json"), encoding="utf-8"))
    if not rec.get("escolhida"): sys.exit("a pipeline não recomendou nenhuma configuração para este caso (nada a verificar)")
    cid = rec["escolhida"]["id"]; hf, cfg = cid.split("|")[:2]; p = dict(x.split(":") for x in cfg.split("+"))
    nome, nivel, kv, racio = hf.split("/")[-1], NIVEL_PESOS[p["quantizacao_pesos"]], p["quantizacao_kv"], p["modo_raciocinio"]
    e = next(x for x in est["estimativas"] if x["id"] == cid)
    alvos = {rot: q for rot, q in e["qualidade"].items() if rot in GENERICAS}
    for rot in e["qualidade"]:
        if rot not in GENERICAS: print(f"aviso: {rot} ainda não é medido por este comando (fica de fora da verificação)")
    if not alvos: sys.exit("nenhuma prova deste caso é medível aqui (só GSM8K, MATH-500, WMT24++ e OAB por enquanto)")
    cid_caso = os.path.basename(caso).split("_")[0]
    CASO.update(modelo=nome, nivel=nivel, kv=kv, raciocinio=racio, caso=cid_caso)
    pasta = a.pasta or pasta_padrao(); os.makedirs(pasta, exist_ok=True)
    print(f"\n>>> {cid_caso}: {hf}, pesos {nivel}, KV {kv}, raciocínio {racio}; provas: {', '.join(alvos)}\n", flush=True)
    dest = os.path.join(medir.MODELOS, nome)
    if not os.path.exists(os.path.join(dest, "config.json")):
        from huggingface_hub import snapshot_download
        snapshot_download(hf, local_dir=dest)
    cmd = [sys.executable, os.path.join(RAIZ, "etapa4_estimativa", "medicao", "medir.py"), "--modelo", nome, "--niveis", nivel, "--benchmarks", *[GENERICAS[r][0] for r in alvos],
           "--kv", kv, "--saida", "kv.csv", "--dir", pasta] + (["--raciocinio-ligado"] if racio == "ligado" else [])
    if a.limite: cmd += ["--limites", *[f"{GENERICAS[r][0]}={a.limite}" for r in alvos]]
    subprocess.run(cmd, check=True)
    linhas = {l["benchmark"]: l for l in csv.DictReader(open(os.path.join(pasta, "kv.csv"), encoding="utf-8")) if l["modelo"] == nome and l["nivel"] == nivel and l["kv"] == kv}
    provas = []
    for rot, q in alvos.items():
        l = linhas.get(GENERICAS[rot][0])
        if l: provas.append({"prova": rot, "base": GENERICAS[rot][1], "n": int(l["n"]), "acuracia": float(l["acuracia"]), "erro_padrao": float(l["erro_padrao"] or 0),
                             "tokens": float(l["tokens_por_resposta"] or 0), "estimado": round(q["valor"] * 100, 2), "meio": q["meio_pts"]})
    versao = subprocess.run([binario(a.llama_dir or medir.BIN, "llama-server"), "--version"], capture_output=True, text=True)
    lat = e["latencia_decodificacao"]; bytes_gib = lat["bytes_pesos_gib"] + lat["bytes_kv_gib_no_ctx"]
    r = {"modelo": f"{hf} (GGUF próprio, {nivel})", "llama_cpp": (versao.stdout + versao.stderr).strip().splitlines()[-1:], "limite": a.limite, "data": time.strftime("%Y-%m-%d %H:%M"),
         "config": {**{k: CASO[k] for k in ("modelo", "nivel", "kv", "raciocinio", "caso")}, "id": cid}, "provas": provas, "banda_gb_s": a.banda, "bytes_gib": bytes_gib, "maquina": platform.node(), "gpu": _gpu()}
    if not a.pular_velocidade:
        v = velocidade(a.llama_dir or medir.BIN, medir.gguf(nome, nivel)); teto = a.banda * 1e9 / (bytes_gib * 2 ** 30)
        r["velocidade"] = {**v, "teto_tok_s": round(teto, 1), "estimado_tok_s": round(teto * lat["eficiencia_banda"], 1), "eficiencia_medida": round(v["tg128_tok_s"] / teto, 3)}
    saida_json = os.path.join(pasta, "resultado.json"); json.dump(r, open(saida_json, "w"), indent=1, ensure_ascii=False)
    print(f"\n=== Caso {cid_caso}: {hf}, pesos {nivel}, KV {kv} ===\n{'prova':<20}{'estimado':>16}{'medido':>16}   veredito")
    for pr in provas:
        m = pr["acuracia"] * 100
        print(f"{pr['prova']:<20}{pr['estimado']:>9.1f} ± {pr['meio']:<4.1f}{m:>9.1f} ± {pr['erro_padrao'] * 100:<4.1f}   {veredito(m, {'nota': pr['estimado'], 'meio': pr['meio']})}")
    if "velocidade" in r:
        v = r["velocidade"]; print(f"\nvelocidade ({r['gpu']}): estimado {v['estimado_tok_s']:.0f} tok/s | medido {v['tg128_tok_s']:.0f} tok/s | eficiência medida {v['eficiencia_medida']:.2f}")
    print(f"\nresultado salvo em {saida_json}")
    if a.limite or a.sem_ingerir: print("não acrescentado à base (" + ("teste rápido" if a.limite else "--sem-ingerir") + ")")
    else: print("\nbase da pipeline:"); ingerir(r)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("caso", nargs="?", help="JSON do caso (casos/*.json)")
    ap.add_argument("--llama-dir", help="pasta com llama-server e llama-bench (padrão: o que estiver no PATH; no modo genérico, o llama.cpp/build/bin do repo)")
    ap.add_argument("--pasta", help="onde guardar as soluções e o resultado (padrão: resultados/<modelo>/<data>_verificacao_<nível>_kv<kv>)")
    ap.add_argument("--banda", type=float, default=BANDA_4090_GB_S, help="banda da GPU em GB/s (padrão: RTX 4090)")
    ap.add_argument("--limite", type=int, default=0, help="só os N primeiros problemas de cada prova (teste rápido); 0 = completo")
    ap.add_argument("--pular-velocidade", action="store_true"); ap.add_argument("--pular-codigo", action="store_true")
    ap.add_argument("--sem-ingerir", action="store_true", help="não acrescenta o resultado à base")
    ap.add_argument("--so-ingerir", metavar="RESULTADO_JSON", help="só acrescenta à base um resultado.json já medido (não roda nada)")
    ap.add_argument("--dry-run", action="store_true", help="com --so-ingerir: mostra o que seria gravado")
    a = ap.parse_args()
    if a.so_ingerir: return ingerir(json.load(open(a.so_ingerir, encoding="utf-8")), a.dry_run)
    if not a.caso: ap.error("informe o JSON do caso (ou --so-ingerir)")
    CASO.update(json.load(open(a.caso, encoding="utf-8")))
    if "gguf_repo" not in CASO: CASO.clear(); return rodar_generico(a)                      # pedido da pipeline (casos_teste/): modo generico, sem codigo
    est = CASO["estimado"]
    media_est = {"nota": sum(e["nota"] for e in est.values()) / len(est), "meio": math.sqrt(sum(e["meio"] ** 2 for e in est.values())) / len(est)}
    pasta = a.pasta or pasta_padrao()
    os.makedirs(pasta, exist_ok=True)
    gguf = baixar()
    versao = subprocess.run([binario(a.llama_dir, "llama-server"), "--version"], capture_output=True, text=True)
    saida_json = os.path.join(pasta, "resultado.json")
    anterior = json.load(open(saida_json)) if os.path.exists(saida_json) else {}                  # --pular-* não apaga o que já foi medido
    bytes_gib = CASO["bytes_pesos_gib"] + CASO["bytes_kv_gib"]
    r = {**{k: anterior[k] for k in ("velocidade", "codigo") if k in anterior},
         "modelo": CASO["gguf_repo"] + "/" + CASO["gguf_arquivo"], "llama_cpp": (versao.stdout + versao.stderr).strip().splitlines()[-1:], "limite": a.limite, "data": time.strftime("%Y-%m-%d %H:%M"),
         "config": {k: CASO[k] for k in ("modelo", "nivel", "kv", "raciocinio", "caso")}, "estimado": est, "banda_gb_s": a.banda, "bytes_gib": bytes_gib,
         "maquina": platform.node(), "gpu": _gpu()}
    if not a.pular_velocidade:
        v = velocidade(a.llama_dir, gguf)
        teto = a.banda * 1e9 / (bytes_gib * 2 ** 30)
        r["velocidade"] = {**v, "teto_tok_s": round(teto, 1), "estimado_tok_s": round(teto * CASO["eficiencia_banda"], 1), "eficiencia_medida": round(v["tg128_tok_s"] / teto, 3)}
    if not a.pular_codigo:
        saidas = gerar(a.llama_dir, gguf, a.limite)
        r["codigo"] = {}
        for bench, sol in saidas.items():
            ok, n = pontuar(bench, sol, pasta)
            r["codigo"][NOMES[bench]] = {"passou": ok, "n": n, "nota": round(100 * ok / n, 2), "tokens_medios": round(sum(s["tokens"] for s in sol) / len(sol), 1),
                                         "erro_padrao_pts": round(100 * math.sqrt((ok / n) * (1 - ok / n) / n), 2)}
        r["codigo"]["media"] = round(sum(r["codigo"][NOMES[b]]["nota"] for b in DATASETS) / 2, 2)
    json.dump(r, open(saida_json, "w"), indent=1, ensure_ascii=False)

    print(f"\n=== Caso {CASO['caso']}: {CASO['modelo']}, pesos {CASO['nivel']}, KV {KV_TIPO[CASO['kv']]} ===")
    if "codigo" in r:
        print(f"{'prova':<12}{'estimado':>16}{'medido':>16}   veredito")
        for b in NOMES.values():
            m, e = r["codigo"][b], est[CHAVE[b]]
            print(f"{b:<12}{e['nota']:>9.1f} ± {e['meio']:<4.1f}{m['nota']:>9.1f} ± {m['erro_padrao_pts']:<4.1f}   {veredito(m['nota'], e)}")
        m = r["codigo"]["media"]
        print(f"{'média':<12}{media_est['nota']:>9.1f} ± {media_est['meio']:<4.1f}{m:>9.1f}          {veredito(m, media_est)}   (é o número da recomendação)")
        if a.limite: print(f"(teste rápido com {a.limite} problemas por prova: o resultado NÃO vale como verificação)")
    if "velocidade" in r:
        v = r["velocidade"]
        print(f"\nvelocidade ({r['gpu']}, {a.banda:g} GB/s): estimado {v['estimado_tok_s']:.0f} tok/s | medido {v['tg128_tok_s']:.0f} tok/s | eficiência medida {v['eficiencia_medida']:.2f} (a ferramenta usa {CASO['eficiencia_banda']})")
    print(f"\nresultado salvo em {saida_json}")
    if a.limite or a.sem_ingerir: print("não acrescentado à base (" + ("teste rápido" if a.limite else "--sem-ingerir") + "); para acrescentar: python etapa7_executar_verificar/verificar.py --so-ingerir " + saida_json)
    else: print("\nbase da pipeline:"); ingerir(r)


if __name__ == "__main__":
    main()
