"""Etapa 7 e 8 (rodar e verificar) para tarefas de código: baixa o GGUF do caso, roda HumanEval+ e MBPP+ completos e a velocidade, e compara com o que a pipeline estimou.
  python verificar.py casos/c8_coder15b.json --llama-dir /caminho/llama.cpp/build/bin                  # tudo
  python verificar.py casos/c8_coder15b.json --llama-dir ... --limite 10 --pular-velocidade            # teste rápido do caminho
  python ingerir.py verificacao_<caso>/resultado.json                                                  # depois, para alimentar a base
Cada caso é um JSON em casos/ (modelo, GGUF, nível, KV e o que a pipeline estimou). Requisitos: llama.cpp compilado com CUDA, e  pip install huggingface_hub datasets evalplus
ATENÇÃO: o evalplus executa o código gerado pelo modelo. Rode em ambiente descartável (container/VM) se puder."""
import argparse, json, math, os, platform, re, shutil, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

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


def baixar(pasta):
    from huggingface_hub import hf_hub_download
    return hf_hub_download(CASO["gguf_repo"], CASO["gguf_arquivo"], local_dir=pasta)


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("caso", help="JSON do caso (casos/*.json)")
    ap.add_argument("--llama-dir", help="pasta com llama-server e llama-bench (padrão: o que estiver no PATH)")
    ap.add_argument("--pasta", help="onde guardar o modelo, as soluções e os resultados (padrão: verificacao_<caso>)")
    ap.add_argument("--banda", type=float, default=BANDA_4090_GB_S, help="banda da GPU em GB/s (padrão: RTX 4090)")
    ap.add_argument("--limite", type=int, default=0, help="só os N primeiros problemas de cada prova (teste rápido); 0 = completo")
    ap.add_argument("--pular-velocidade", action="store_true"); ap.add_argument("--pular-codigo", action="store_true")
    a = ap.parse_args()
    CASO.update(json.load(open(a.caso, encoding="utf-8")))
    est = CASO["estimado"]
    media_est = {"nota": sum(e["nota"] for e in est.values()) / len(est), "meio": math.sqrt(sum(e["meio"] ** 2 for e in est.values())) / len(est)}
    pasta = a.pasta or f"verificacao_{CASO['caso']}"
    os.makedirs(pasta, exist_ok=True)
    gguf = baixar(pasta)
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
    print(f"\nresultado salvo em {saida_json}\npara alimentar a base da pipeline: python etapa8_verificacao/ingerir.py {saida_json}")


if __name__ == "__main__":
    main()
