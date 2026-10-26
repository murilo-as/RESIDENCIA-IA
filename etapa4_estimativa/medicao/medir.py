"""Medicao dos benchmarks por modelo e nivel de quantizacao. Retomavel: pula o que ja esta no CSV.
Uso: medir.py --modelo Qwen2.5-7B-Instruct [--niveis f16 q8_0 q4_k_m] [--benchmarks ...] [--limites mmlu=25 oab=100] [--sem-raciocinio] [--respeitar-etapa1] [--dir DIR]
     medir.py --ingerir-codigo [--dir DIR]   (le a pontuacao do evalplus e grava as linhas de HumanEval+ e MBPP+)"""
import argparse, csv, datetime, gc, json, math, os, random, shutil, signal, subprocess, sys, time, traceback, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
PILOTO = os.path.abspath(os.path.join(AQUI, "..", "..", "piloto"))
MODELOS = "/beegfs/home/user_muriloalves/work/models"
TMP_CODIGO = "/beegfs/home/user_muriloalves/work/tmp_codigo"
LLAMA = os.path.join(PILOTO, "llama.cpp")
BIN = os.path.join(LLAMA, "build", "bin")
VENV_PY = os.path.join(PILOTO, "venv", "bin", "python")
PROXY = os.path.join(PILOTO, "04_gsm8k", "proxy.py")
TAREFAS = os.path.join(AQUI, "tasks")
CAMPOS = ["modelo", "nivel", "benchmark", "n", "acuracia", "erro_padrao", "tempo_s", "tokens_por_resposta", "cortadas", "commit_llama_cpp", "data"]
TIPO = {"f16": None, "q8_0": "Q8_0", "q4_k_m": "Q4_K_M"}
MIN_LIVRE = 80e9
MAX_MODELOS = 450e9  # a home tem limite de 500 GB; as outras pastas somam ~27 GB
SEMENTES = dict(random_seed=42, numpy_random_seed=42, torch_random_seed=42, fewshot_random_seed=42)

# benchmark -> task do lm-eval (log-prob pelo hf) / (gerativo pelo llama-server) / (codigo: gerar aqui, pontuar em job isolado)
LOGLIK = {"mmlu": dict(task="mmlu", fewshot=5, limite=25), "mmlu_completo": dict(task="mmlu", fewshot=5),
          "medqa": dict(task="medqa_4options"), "oab": dict(task="oab_exams_5shot", fewshot=5, sorteio=True), "pubmedqa": dict(task="pubmedqa_qiaojin"),
          "gpqa": dict(task="gpqa_diamond_zeroshot", token=True)}
GERATIVO = {"gsm8k": dict(task="gsm8k"), "math500": dict(task="minerva_math500"), "wmt24": dict(task="wmt24pp_en_pt_br")}
CODIGO = {"humaneval": "humaneval", "mbpp": "mbpp"}
ORDEM = ["mmlu", "mmlu_completo", "medqa", "oab", "pubmedqa", "gpqa", "gsm8k", "humaneval", "mbpp", "wmt24", "math500"]  # log-prob (hf) antes dos gerativos (llama-server)
PRIMARIA = {"humaneval": "humaneval_plus", "mbpp": "mbpp_plus"}  # nome da linha principal no CSV; os demais usam o proprio nome


def tamanho_dir(p): return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs if os.path.isfile(os.path.join(d, f)))


def agora(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def num(x):
    try: return round(float(x), 6)
    except (TypeError, ValueError): return ""


def erro_binomial(p, n): return round(math.sqrt(p * (1 - p) / n), 6) if n else ""


class Medicao:
    def __init__(self, pasta):
        self.pasta = pasta
        os.makedirs(pasta, exist_ok=True)
        self.csv = os.path.join(pasta, "resultados.csv")
        self.erros = os.path.join(pasta, "erros.log")
        self.parar = os.path.join(AQUI, "PARAR")
        self.teste = os.path.abspath(pasta) != AQUI  # --dir diferente: amostras de codigo com prefixo teste_
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
        livre, usado = shutil.disk_usage(MODELOS).free, tamanho_dir(MODELOS)
        if livre < MIN_LIVRE or usado > MAX_MODELOS:
            msg = (f"espaco livre {livre / 1e9:.1f} GB abaixo de 80 GB" if livre < MIN_LIVRE else f"pasta de modelos com {usado / 1e9:.0f} GB (limite {MAX_MODELOS / 1e9:.0f} GB)") + f": parando (criado {self.parar})"
            self.log_erro(quem, "-", "-", msg)
            open(self.parar, "w").write(msg + "\n")
            return False
        return True

    def tm(self):
        if self._tm is None:
            from lm_eval.tasks import TaskManager
            t0 = time.perf_counter()
            self._tm = TaskManager(include_path=TAREFAS)
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


def esperar_servidor(proc, limite=1200):
    t0 = time.time()
    while time.time() - t0 < limite:
        if proc.poll() is not None: raise RuntimeError(f"llama-server saiu com codigo {proc.returncode}")
        try:
            if urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5).status == 200: return
        except Exception: pass
        time.sleep(3)
    raise RuntimeError("llama-server nao ficou pronto")


def esperar_porta(proc, porta=8081, limite=120):
    """Espera o proxy aceitar conexoes (a subida pode passar de 3 s com o disco ocupado)."""
    import socket
    t0 = time.time()
    while time.time() - t0 < limite:
        if proc.poll() is not None: raise RuntimeError(f"proxy saiu com codigo {proc.returncode}")
        try:
            socket.create_connection(("127.0.0.1", porta), timeout=2).close()
            return
        except OSError: time.sleep(1)
    raise RuntimeError("proxy nao abriu a porta")


def matar(proc):
    if proc is None or proc.poll() is not None: return
    proc.terminate()
    try: proc.wait(30)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait()


class Sessao:
    """Um (modelo, nivel): carrega o hf ou sobe o llama-server so quando um benchmark precisa, e libera o outro."""
    def __init__(self, m, modelo, nivel, raciocinio):
        self.m, self.modelo, self.nivel, self.raciocinio = m, modelo, nivel, raciocinio
        self._lm = self._srv = self._path = None

    def path(self):
        if self._path is None: self._path = garantir_gguf(self.m, self.modelo, self.nivel)
        return self._path

    def hf(self):
        self.fechar_servidor()
        if self._lm is None:
            import torch
            from lm_eval.models.huggingface import HFLM
            self._lm = HFLM(pretrained=MODELOS, gguf_file=os.path.basename(self.path()), tokenizer=os.path.join(MODELOS, self.modelo), dtype="float16", batch_size=16, device="cuda")
            torch.cuda.synchronize()
        return self._lm

    def fechar_hf(self):
        if self._lm is not None:
            self._lm = None
            liberar_gpu()

    def servidor(self):
        self.fechar_hf()
        if self._srv is None or self._srv.poll() is not None:
            matar(self._srv)
            cmd = [os.path.join(BIN, "llama-server"), "-m", self.path(), "-ngl", "99", "-np", "8", "-c", "32768", "--host", "127.0.0.1", "--port", "8080"]
            if not self.raciocinio: cmd += ["--chat-template-kwargs", '{"enable_thinking":false}']
            self._srv = subprocess.Popen(cmd, stdout=open(log_servidor(self.modelo, self.nivel), "w"), stderr=subprocess.STDOUT)
            esperar_servidor(self._srv)
        return self._srv

    def fechar_servidor(self):
        matar(self._srv)
        self._srv = None

    def fechar(self):
        self.fechar_servidor()
        self.fechar_hf()


def amostra_dir(m, s, bench): return os.path.join(m.pasta, "amostras", s.modelo, s.nivel, bench, time.strftime("%Y%m%dT%H%M%S"))


def salvar(tracker, res):
    amostras = res.pop("samples")
    tracker.save_results_aggregated(results=res, samples=amostras)
    for t in res["configs"]: tracker.save_results_samples(task_name=t, samples=amostras[t])


def rodar_loglik(m, s, bench, limite):
    from lm_eval.loggers import EvaluationTracker
    cfg = LOGLIK[bench]
    if cfg.get("token") and not os.environ.get("HF_TOKEN"): raise RuntimeError("HF_TOKEN ausente no ambiente do job")
    task = cfg["task"]
    lm = s.hf()
    m.preparar(task)
    tracker = EvaluationTracker(output_path=amostra_dir(m, s, bench))
    t0 = time.perf_counter()
    sel = dict(limit=limite or None)
    if cfg.get("sorteio") and limite:  # sorteia `limite` questoes com seed 42 (as mesmas nos 3 modelos), em vez de pegar as primeiras
        total = len(m._carregado[task]["tasks"][task].eval_docs)
        sel = dict(samples={task: sorted(random.Random(42).sample(range(total), limite))})
    res = m.avaliar(task, model=lm, num_fewshot=cfg.get("fewshot"), log_samples=True, evaluation_tracker=tracker, **sel)
    tempo = time.perf_counter() - t0
    salvar(tracker, res)
    if task == "mmlu":
        g = res["groups"]["mmlu"]
        n = sum(v["effective"] for v in res["n-samples"].values())
    else:
        g = res["results"][task]
        n = res["n-samples"][task]["effective"]
    m.gravar(modelo=s.modelo, nivel=s.nivel, benchmark=bench, n=n, acuracia=num(g["acc,none"]), erro_padrao=num(g["acc_stderr,none"]), tempo_s=round(tempo, 1))
    print(f"{bench} {s.modelo} {s.nivel}: n={n} acc={g['acc,none']:.4f} em {tempo:.0f} s", flush=True)


def stats_proxy(log):
    regs = [json.loads(l) for l in open(log)] if os.path.exists(log) else []
    ok = [r for r in regs if "completion_tokens" in r]
    return round(sum(r["completion_tokens"] for r in ok) / max(len(ok), 1), 1), sum(r["finish_reason"] == "length" for r in ok)


def rodar_gerativo(m, s, bench, limite):
    from lm_eval.loggers import EvaluationTracker
    task = GERATIVO[bench]["task"]
    s.servidor()
    saida = amostra_dir(m, s, bench)
    os.makedirs(saida, exist_ok=True)
    proxy_log = os.path.join(saida, "proxy.jsonl")
    proxy = subprocess.Popen([VENV_PY, PROXY, "http://127.0.0.1:8080", proxy_log, "8081"])
    try:
        esperar_porta(proxy)
        m.preparar(task)
        tracker = EvaluationTracker(output_path=saida)
        t0 = time.perf_counter()
        res = m.avaliar(task, model="local-chat-completions",
                        model_args="model=qwen,base_url=http://127.0.0.1:8081/v1/chat/completions,num_concurrent=8,max_retries=1,tokenized_requests=False,timeout=3600",
                        limit=limite or None, apply_chat_template=True, fewshot_as_multiturn=True, gen_kwargs="temperature=0,max_gen_toks=2048",
                        log_samples=True, evaluation_tracker=tracker)
        tempo = time.perf_counter() - t0
        salvar(tracker, res)
    finally:
        matar(proxy)
    tokens, cortadas = stats_proxy(proxy_log)
    r = res["results"][task]
    n = res["n-samples"][task]["effective"]
    comum = dict(modelo=s.modelo, nivel=s.nivel, n=n, tempo_s=round(tempo, 1), tokens_por_resposta=tokens, cortadas=cortadas)
    if bench == "gsm8k":
        m.gravar(benchmark="gsm8k", acuracia=num(r["exact_match,flexible-extract"]), erro_padrao=num(r["exact_match_stderr,flexible-extract"]), **comum)
        m.gravar(benchmark="gsm8k_strict", acuracia=num(r["exact_match,strict-match"]), erro_padrao=num(r["exact_match_stderr,strict-match"]), **comum)
        print(f"gsm8k {s.modelo} {s.nivel}: n={n} flexible={r['exact_match,flexible-extract']:.4f} tokens/resp={tokens} cortadas={cortadas} em {tempo:.0f} s", flush=True)
    elif bench == "math500":
        m.gravar(benchmark="math500", acuracia=num(r["math_verify,none"]), erro_padrao=num(r.get("math_verify_stderr,none")), **comum)
        m.gravar(benchmark="math500_strict", acuracia=num(r["exact_match,none"]), erro_padrao=num(r.get("exact_match_stderr,none")), **comum)
        print(f"math500 {s.modelo} {s.nivel}: n={n} math_verify={r['math_verify,none']:.4f} exact_match={r['exact_match,none']:.4f} tokens/resp={tokens} cortadas={cortadas} em {tempo:.0f} s", flush=True)
    else:
        se = r.get("chrf_stderr,none")  # chrF gravado dividido por 100 (0 a 1) na coluna acuracia
        m.gravar(benchmark="wmt24", acuracia=num(r["chrf,none"] / 100), erro_padrao=num(se / 100) if isinstance(se, (int, float)) else "", **comum)
        print(f"wmt24 {s.modelo} {s.nivel}: n={n} chrF={r['chrf,none']:.2f} tokens/resp={tokens} cortadas={cortadas} em {tempo:.0f} s", flush=True)


def rodar_codigo(m, s, bench, limite):
    """Gera as solucoes (nao executa codigo). A pontuacao e o CSV vem depois: pontuar_codigo.py (job isolado) e --ingerir-codigo."""
    import codigo
    saida = os.path.join(m.pasta, "amostras", s.modelo, s.nivel, bench)
    stats = os.path.join(saida, "geracao.json")
    prefixo = "teste_" if m.teste else ""
    jsonl = os.path.join(TMP_CODIGO, "samples", f"{prefixo}{s.modelo}__{s.nivel}__{bench}.jsonl")
    if os.path.exists(stats) and os.path.exists(jsonl):
        print(f"{bench} {s.modelo} {s.nivel}: geracao ja existe", flush=True)
        return
    s.servidor()
    os.makedirs(saida, exist_ok=True)
    os.makedirs(os.path.dirname(jsonl), exist_ok=True)
    shutil.copy(os.path.join(AQUI, "pontuar_codigo.py"), os.path.join(TMP_CODIGO, "pontuar_codigo.py"))
    saidas, tempo = codigo.gerar(bench, limite)
    with open(jsonl + ".parcial", "w") as f: f.write("\n".join(json.dumps({"task_id": x["task_id"], "solution": x["solution"]}) for x in saidas) + "\n")
    os.replace(jsonl + ".parcial", jsonl)
    tok = [x["tokens"] for x in saidas]
    json.dump({"n": len(saidas), "tempo_s": tempo, "tokens_por_resposta": sum(tok) / len(tok), "cortadas": sum(x["finish_reason"] == "length" for x in saidas),
               "medidas": [{k: x[k] for k in ("task_id", "tokens", "finish_reason", "segundos")} for x in saidas]}, open(stats, "w"))
    print(f"{bench} {s.modelo} {s.nivel}: {len(saidas)} solucoes geradas em {tempo:.0f} s, tokens/resp {sum(tok) / len(tok):.0f}", flush=True)


def ingerir_codigo(m):
    """Le a pontuacao do evalplus (TMP_CODIGO/resultados_codigo) e grava as linhas de HumanEval+ e MBPP+ no CSV."""
    prefixo = "teste_" if m.teste else ""
    novos = 0
    for modelo in sorted(os.listdir(os.path.join(m.pasta, "amostras"))) if os.path.isdir(os.path.join(m.pasta, "amostras")) else []:
        for nivel in sorted(os.listdir(os.path.join(m.pasta, "amostras", modelo))):
            for bench in CODIGO:
                pasta = os.path.join(m.pasta, "amostras", modelo, nivel, bench)
                stats, pont = os.path.join(pasta, "geracao.json"), os.path.join(TMP_CODIGO, "resultados_codigo", f"{prefixo}{modelo}__{nivel}__{bench}.json")
                if not (os.path.exists(stats) and os.path.exists(pont)) or (modelo, nivel, PRIMARIA[bench]) in m.feitos(): continue
                g, p = json.load(open(stats)), json.load(open(pont))
                n = p["n"]
                comum = dict(modelo=modelo, nivel=nivel, n=n, tempo_s=round(g["tempo_s"], 1), tokens_por_resposta=round(g["tokens_por_resposta"], 1), cortadas=g["cortadas"])
                m.gravar(benchmark=PRIMARIA[bench], acuracia=num(p["plus"] / n), erro_padrao=erro_binomial(p["plus"] / n, n), **comum)
                m.gravar(benchmark=f"{bench}_base", acuracia=num(p["base"] / n), erro_padrao=erro_binomial(p["base"] / n, n), **comum)
                shutil.copy(pont, os.path.join(pasta, "pontuacao.json"))
                novos += 1
                print(f"{bench} {modelo} {nivel}: base {p['base']}/{n}, plus {p['plus']}/{n}", flush=True)
    print(f"{novos} combinacoes de codigo ingeridas", flush=True)


def nome_csv(bench): return PRIMARIA.get(bench, bench)


def main():
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo")
    ap.add_argument("--niveis", nargs="+", default=["f16", "q8_0", "q4_k_m"], choices=list(TIPO))
    ap.add_argument("--benchmarks", nargs="+", default=[b for b in ORDEM if b != "mmlu_completo"], choices=ORDEM)
    ap.add_argument("--limites", nargs="*", default=[], help="nome=N (0 = completo); padrao: mmlu=25, o resto completo")
    ap.add_argument("--sem-raciocinio", action="store_true", help="desliga o raciocinio (enable_thinking=false) nos gerativos")
    ap.add_argument("--respeitar-etapa1", action="store_true", help="pula os benchmarks marcados como pulados em etapa1.json")
    ap.add_argument("--ingerir-codigo", action="store_true")
    ap.add_argument("--dir", default=AQUI)
    a = ap.parse_args()
    m = Medicao(a.dir)
    if a.ingerir_codigo:
        ingerir_codigo(m)
        return
    if not a.modelo: ap.error("--modelo e obrigatorio")
    if os.path.exists(m.parar):
        m.log_erro(a.modelo, "-", "-", f"{m.parar} existe: nada a fazer")
        sys.exit(3)
    if not m.espaco_ok(a.modelo): sys.exit(3)
    limites = {k: int(v) for k, v in (x.split("=") for x in a.limites)}
    ativos = [b for b in ORDEM if b in a.benchmarks]
    if a.respeitar_etapa1:
        e1 = json.load(open(os.path.join(AQUI, "etapa1.json")))
        for b in list(ativos):
            if e1.get(b, {}).get("status") == "pulado":
                print(f"pula {b}: etapa 1 -> {e1[b].get('motivo')}", flush=True)
                ativos.remove(b)
    falhou = False
    for nivel in a.niveis:
        s = Sessao(m, a.modelo, nivel, not a.sem_raciocinio)
        try:
            for bench in ativos:
                if (a.modelo, nivel, nome_csv(bench)) in m.feitos():
                    print(f"pula {a.modelo} {nivel} {bench}: ja no CSV", flush=True)
                    continue
                if os.path.exists(m.parar): sys.exit(3)
                print(f"##### {a.modelo} {nivel} {bench} ({agora()})", flush=True)
                limite = limites.get(bench, LOGLIK.get(bench, {}).get("limite", 0))
                try:
                    if bench in LOGLIK: rodar_loglik(m, s, bench, limite)
                    elif bench in GERATIVO: rodar_gerativo(m, s, bench, limite)
                    else: rodar_codigo(m, s, bench, limite)
                except Exception:
                    falhou = True
                    m.log_erro(a.modelo, nivel, bench, traceback.format_exc())
                    s.fechar_servidor()
        finally:
            s.fechar()
    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main()
