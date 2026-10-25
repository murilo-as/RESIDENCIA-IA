"""Fase A: MMLU (hf + gguf_file) e GSM8K (llama-server + proxy) por modelo e nivel de quantizacao. Retomavel: pula o que ja esta no CSV.
Uso: medir.py --modelo Qwen2.5-7B-Instruct [--niveis f16 q8_0 q4_k_m] [--benchmarks mmlu gsm8k] [--mmlu-limit 25] [--gsm8k-limit 0] [--dir DIR]"""
import argparse, csv, datetime, gc, json, os, shutil, signal, subprocess, sys, time, traceback, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
PILOTO = os.path.abspath(os.path.join(AQUI, "..", "..", "piloto"))
MODELOS = "/beegfs/home/user_muriloalves/work/models"
LLAMA = os.path.join(PILOTO, "llama.cpp")
BIN = os.path.join(LLAMA, "build", "bin")
VENV_PY = os.path.join(PILOTO, "venv", "bin", "python")
PROXY = os.path.join(PILOTO, "04_gsm8k", "proxy.py")
CAMPOS = ["modelo", "nivel", "benchmark", "n", "acuracia", "erro_padrao", "tempo_s", "tokens_por_resposta", "cortadas", "commit_llama_cpp", "data"]
TIPO = {"f16": None, "q8_0": "Q8_0", "q4_k_m": "Q4_K_M"}
MIN_LIVRE = 80e9
SEMENTES = dict(random_seed=42, numpy_random_seed=42, torch_random_seed=42, fewshot_random_seed=42)


def agora(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Medicao:
    def __init__(self, pasta):
        self.pasta = pasta
        os.makedirs(pasta, exist_ok=True)
        self.csv = os.path.join(pasta, "resultados.csv")
        self.erros = os.path.join(pasta, "erros.log")
        self.parar = os.path.join(AQUI, "PARAR")
        self.commit = subprocess.run(["git", "-C", LLAMA, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self._tm = None
        self._carregado = {}

    def log_erro(self, modelo, nivel, bench, msg):
        with open(self.erros, "a") as f: f.write(f"{agora()} {modelo} {nivel} {bench}: {msg}\n")
        print(f"ERRO {modelo} {nivel} {bench}: {msg[:2000]}", flush=True)

    def feitos(self):
        if not os.path.exists(self.csv): return set()
        return {(r["modelo"], r["nivel"], r["benchmark"]) for r in csv.DictReader(open(self.csv))}

    def gravar(self, **linha):
        novo = not os.path.exists(self.csv)
        with open(self.csv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS)
            if novo: w.writeheader()
            w.writerow({**{c: "" for c in CAMPOS}, **linha, "commit_llama_cpp": self.commit, "data": agora()})
            f.flush(); os.fsync(f.fileno())

    def espaco_ok(self, quem):
        livre = shutil.disk_usage(MODELOS).free
        if livre < MIN_LIVRE:
            msg = f"espaco livre {livre / 1e9:.1f} GB abaixo de 80 GB: parando (criado {self.parar})"
            self.log_erro(quem, "-", "-", msg)
            open(self.parar, "w").write(msg + "\n")
            return False
        return True

    def tm(self):
        if self._tm is None:
            from lm_eval.tasks import TaskManager
            t0 = time.perf_counter()
            self._tm = TaskManager()
            print(f"TaskManager criado em {time.perf_counter() - t0:.1f} s", flush=True)
        return self._tm

    def preparar(self, nome):
        """Cria o TaskManager e monta a tarefa (uma vez por processo), fora do tempo medido."""
        tm = self.tm()
        if nome not in self._carregado:
            t0 = time.perf_counter()
            self._carregado[nome] = tm.load([nome])
            print(f"tarefa {nome} montada em {time.perf_counter() - t0:.1f} s", flush=True)

    def avaliar(self, nome, **kw):
        """simple_evaluate reaproveitando o TaskManager e as tarefas ja montadas."""
        from lm_eval import simple_evaluate
        self.preparar(nome)
        tm = self.tm()

        class Pronto:
            def __init__(s, c): s.c = c
            def load(s, tasks): return s.c
            def __getattr__(s, k): return getattr(tm, k)

        return simple_evaluate(tasks=[nome], task_manager=Pronto(self._carregado[nome]), **SEMENTES, **kw)


def gguf(modelo, nivel): return os.path.join(MODELOS, f"{modelo.lower()}-{nivel}.gguf")


def log_servidor(modelo, nivel):
    pasta = os.path.join(AQUI, "logs", "servidor")
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, f"{modelo}_{nivel}_{time.strftime('%Y%m%dT%H%M%S')}.log")


def garantir_gguf(m, modelo, nivel):
    destino = gguf(modelo, nivel)
    if os.path.exists(destino): return destino
    f16 = gguf(modelo, "f16")
    if not os.path.exists(f16):
        if not m.espaco_ok(modelo): raise RuntimeError("sem espaco livre")
        parcial = f16 + ".parcial"
        subprocess.run([VENV_PY, os.path.join(LLAMA, "convert_hf_to_gguf.py"), os.path.join(MODELOS, modelo), "--outtype", "f16", "--outfile", parcial], check=True)
        os.replace(parcial, f16)
    if nivel != "f16":
        if not m.espaco_ok(modelo): raise RuntimeError("sem espaco livre")
        parcial = destino + ".parcial"
        subprocess.run([os.path.join(BIN, "llama-quantize"), f16, parcial, TIPO[nivel]], check=True)
        os.replace(parcial, destino)
    return destino


def liberar_gpu():
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception: pass


def rodar_mmlu(m, modelo, nivel, limit):
    import torch
    from lm_eval.loggers import EvaluationTracker
    from lm_eval.models.huggingface import HFLM
    path = garantir_gguf(m, modelo, nivel)
    saida = os.path.join(m.pasta, "amostras", modelo, nivel, "mmlu", time.strftime("%Y%m%dT%H%M%S"))
    lm = HFLM(pretrained=MODELOS, gguf_file=os.path.basename(path), tokenizer=os.path.join(MODELOS, modelo), dtype="float16", batch_size=16, device="cuda")
    try:
        torch.cuda.synchronize()
        m.preparar("mmlu")
        tracker = EvaluationTracker(output_path=saida)
        t0 = time.perf_counter()
        res = m.avaliar("mmlu", model=lm, num_fewshot=5, limit=limit, log_samples=True, evaluation_tracker=tracker)
        tempo = time.perf_counter() - t0
        amostras = res.pop("samples")
        tracker.save_results_aggregated(results=res, samples=amostras)
        for t in res["configs"]: tracker.save_results_samples(task_name=t, samples=amostras[t])
    finally:
        del lm
        liberar_gpu()
    g = res["groups"]["mmlu"]
    n = sum(v["effective"] for v in res["n-samples"].values())
    m.gravar(modelo=modelo, nivel=nivel, benchmark="mmlu", n=n, acuracia=round(g["acc,none"], 6), erro_padrao=round(g["acc_stderr,none"], 6), tempo_s=round(tempo, 1))
    print(f"mmlu {modelo} {nivel}: n={n} acc={g['acc,none']:.4f} +- {g['acc_stderr,none']:.4f} em {tempo:.0f} s", flush=True)


def esperar_servidor(proc, limite=900):
    t0 = time.time()
    while time.time() - t0 < limite:
        if proc.poll() is not None: raise RuntimeError(f"llama-server saiu com codigo {proc.returncode}")
        try:
            if urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5).status == 200: return
        except Exception: pass
        time.sleep(3)
    raise RuntimeError("llama-server nao ficou pronto")


def matar(proc):
    if proc is None or proc.poll() is not None: return
    proc.terminate()
    try: proc.wait(30)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait()


def rodar_gsm8k(m, modelo, nivel, limit):
    from lm_eval.loggers import EvaluationTracker
    path = garantir_gguf(m, modelo, nivel)
    saida = os.path.join(m.pasta, "amostras", modelo, nivel, "gsm8k", time.strftime("%Y%m%dT%H%M%S"))
    os.makedirs(saida, exist_ok=True)
    proxy_log = os.path.join(saida, "proxy.jsonl")
    servidor = proxy = None
    try:
        servidor = subprocess.Popen([os.path.join(BIN, "llama-server"), "-m", path, "-ngl", "99", "-np", "8", "-c", "32768", "--host", "127.0.0.1", "--port", "8080"],
                                    stdout=open(log_servidor(modelo, nivel), "w"), stderr=subprocess.STDOUT)
        esperar_servidor(servidor)
        proxy = subprocess.Popen([VENV_PY, PROXY, "http://127.0.0.1:8080", proxy_log, "8081"])
        time.sleep(3)
        m.preparar("gsm8k")
        tracker = EvaluationTracker(output_path=saida)
        t0 = time.perf_counter()
        res = m.avaliar("gsm8k", model="local-chat-completions",
                        model_args="model=qwen,base_url=http://127.0.0.1:8081/v1/chat/completions,num_concurrent=8,max_retries=1,tokenized_requests=False",
                        limit=limit or None, apply_chat_template=True, fewshot_as_multiturn=True, gen_kwargs="temperature=0,max_gen_toks=2048",
                        log_samples=True, evaluation_tracker=tracker)
        tempo = time.perf_counter() - t0
        amostras = res.pop("samples")
        tracker.save_results_aggregated(results=res, samples=amostras)
        for t in res["configs"]: tracker.save_results_samples(task_name=t, samples=amostras[t])
    finally:
        matar(proxy)
        matar(servidor)
        liberar_gpu()
    regs = [json.loads(l) for l in open(proxy_log)]
    ok = [r for r in regs if "completion_tokens" in r]
    tokens = sum(r["completion_tokens"] for r in ok) / max(len(ok), 1)
    cortadas = sum(r["finish_reason"] == "length" for r in ok)
    r = res["results"]["gsm8k"]
    n = res["n-samples"]["gsm8k"]["effective"]
    comum = dict(modelo=modelo, nivel=nivel, n=n, tempo_s=round(tempo, 1), tokens_por_resposta=round(tokens, 1), cortadas=cortadas)
    m.gravar(benchmark="gsm8k", acuracia=round(r["exact_match,flexible-extract"], 6), erro_padrao=round(r["exact_match_stderr,flexible-extract"], 6), **comum)
    m.gravar(benchmark="gsm8k_strict", acuracia=round(r["exact_match,strict-match"], 6), erro_padrao=round(r["exact_match_stderr,strict-match"], 6), **comum)
    print(f"gsm8k {modelo} {nivel}: n={n} flexible={r['exact_match,flexible-extract']:.4f} strict={r['exact_match,strict-match']:.4f} tokens/resp={tokens:.0f} cortadas={cortadas} em {tempo:.0f} s", flush=True)


def main():
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True)
    ap.add_argument("--niveis", nargs="+", default=["f16", "q8_0", "q4_k_m"], choices=list(TIPO))
    ap.add_argument("--benchmarks", nargs="+", default=["mmlu", "gsm8k"], choices=["mmlu", "gsm8k"])
    ap.add_argument("--mmlu-limit", type=int, default=25)
    ap.add_argument("--gsm8k-limit", type=int, default=0, help="0 = as 1319 questoes")
    ap.add_argument("--dir", default=AQUI)
    a = ap.parse_args()
    m = Medicao(a.dir)
    if os.path.exists(m.parar):
        m.log_erro(a.modelo, "-", "-", f"{m.parar} existe: nada a fazer")
        sys.exit(3)
    if not m.espaco_ok(a.modelo): sys.exit(3)
    falhou = False
    for nivel in a.niveis:
        for bench in a.benchmarks:
            if (a.modelo, nivel, bench) in m.feitos():
                print(f"pula {a.modelo} {nivel} {bench}: ja no CSV", flush=True)
                continue
            if os.path.exists(m.parar): sys.exit(3)
            print(f"##### {a.modelo} {nivel} {bench} ({agora()})", flush=True)
            try:
                rodar_mmlu(m, a.modelo, nivel, a.mmlu_limit) if bench == "mmlu" else rodar_gsm8k(m, a.modelo, nivel, a.gsm8k_limit)
            except Exception:
                falhou = True
                m.log_erro(a.modelo, nivel, bench, traceback.format_exc())
    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main()
