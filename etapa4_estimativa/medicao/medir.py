"""Medicao dos benchmarks por modelo e nivel de quantizacao. Retomavel: pula o que ja esta no CSV.
Uso: medir.py --modelo Qwen2.5-7B-Instruct [--niveis f16 q8_0 q4_k_m] [--benchmarks ...] [--limites mmlu=25 oab=100] [--sem-raciocinio] [--respeitar-etapa1] [--dir DIR]
     medir.py ... --kv 8 --saida kv.csv            (KV quantizado: grava em kv.csv, com as colunas kv e raciocinio)
     medir.py ... --raciocinio-ligado              (raciocinio ligado, 4096 tokens: grava em raciocinio.csv)
     medir.py --ingerir-codigo [--dir DIR]         (le a pontuacao do evalplus e grava as linhas de HumanEval+ e MBPP+)"""
import argparse, ast, csv, datetime, gc, json, math, os, random, shutil, signal, subprocess, sys, time, traceback, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
PILOTO = os.path.abspath(os.path.join(AQUI, "..", "..", "piloto"))
MODELOS = "/beegfs/home/user_muriloalves/work/models"
TMP_CODIGO = "/beegfs/home/user_muriloalves/work/tmp_codigo"
LLAMA = os.path.join(PILOTO, "llama.cpp")
BIN = os.path.join(LLAMA, "build", "bin")
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
VENV_PY = next((v for v in (os.path.join(RAIZ, "venv", "bin", "python"), os.path.join(PILOTO, "venv", "bin", "python")) if os.path.exists(v)), os.path.join(RAIZ, "venv", "bin", "python"))  # venv na raiz do projeto; piloto/venv como reserva
PROXY = os.path.join(PILOTO, "04_gsm8k", "proxy.py")
TAREFAS = os.path.join(AQUI, "tasks")
CAMPOS = ["modelo", "nivel", "benchmark", "n", "acuracia", "erro_padrao", "tempo_s", "tokens_por_resposta", "cortadas", "commit_llama_cpp", "data"]
TIPO = {"f16": None, "q8_0": "Q8_0", "q4_k_m": "Q4_K_M"}
MIN_LIVRE = 80e9
MAX_MODELOS = 450e9  # a home tem limite de 500 GB; as outras pastas somam ~27 GB
SEMENTES = dict(random_seed=42, numpy_random_seed=42, torch_random_seed=42, fewshot_random_seed=42)

CAMPOS_EXT = CAMPOS[:2] + ["kv", "raciocinio"] + CAMPOS[2:]  # kv.csv e raciocinio.csv
KV_TIPOS = {"16": ("f16", "f16"), "8": ("q8_0", "q8_0"), "4": ("q4_0", "q4_0"), "k4v8": ("q4_0", "q8_0")}  # nome na coluna kv -> (tipo do K, tipo do V)
BYTES_KV = {"f16": 2, "q8_0": 34 / 32, "q4_0": 18 / 32}  # bytes por elemento
# benchmark -> task do lm-eval (log-prob pelo hf) / (gerativo pelo llama-server) / (codigo: gerar aqui, pontuar em job isolado) / (letra: gerar a letra, letra.py)
LOGLIK = {"mmlu": dict(task="mmlu", fewshot=5, limite=25), "mmlu_completo": dict(task="mmlu", fewshot=5),
          "mmlu_logprob_fp16": dict(task="mmlu", fewshot=5, limite=25, dtype="float16"), "mmlu_logprob_bf16": dict(task="mmlu", fewshot=5, limite=25, dtype="bfloat16"),
          "medqa": dict(task="medqa_4options"), "oab": dict(task="oab_exams_5shot", fewshot=5, sorteio=True), "pubmedqa": dict(task="pubmedqa_qiaojin"),
          "gpqa": dict(task="gpqa_diamond_zeroshot", token=True)}
GERATIVO = {"gsm8k": dict(task="gsm8k"), "math500": dict(task="minerva_math500"), "wmt24": dict(task="wmt24pp_en_pt_br")}
CODIGO = {"humaneval": "humaneval", "mbpp": "mbpp"}
LETRA = {"mmlu_letra": dict(limite=25), "oab_letra": dict(limite=0)}  # limite = questoes por assunto (mmlu) ou total (oab); 0 = todas
ORDEM = ["mmlu", "mmlu_completo", "mmlu_logprob_fp16", "mmlu_logprob_bf16", "medqa", "oab", "pubmedqa", "gpqa",
         "gsm8k", "humaneval", "mbpp", "wmt24", "math500", "mmlu_letra", "oab_letra"]  # log-prob (hf) antes dos que usam o llama-server
PRIMARIA = {"humaneval": "humaneval_plus", "mbpp": "mbpp_plus"}  # nome da linha principal no CSV; os demais usam o proprio nome
REUSO = {"gsm8k": [("gsm8k", "gsm8k"), ("gsm8k_strict", "gsm8k_strict")], "math500": [("math500", "math500"), ("math500_strict", "math500_strict")],
         "mmlu_logprob_fp16": [("mmlu", "mmlu_logprob_fp16")]}  # benchmark -> [(linha em resultados.csv, linha gravada)]: mesma configuracao, nao precisa repetir


def tamanho_dir(p): return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs if os.path.isfile(os.path.join(d, f)))


def agora(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def num(x):
    try: return round(float(x), 6)
    except (TypeError, ValueError): return ""


def erro_binomial(p, n): return round(math.sqrt(p * (1 - p) / n), 6) if n else ""


class Medicao:
    def __init__(self, pasta, saida="resultados.csv", extras=None):
        """extras: colunas fixas desta execucao (kv, raciocinio) -> o CSV e kv.csv/raciocinio.csv, com CAMPOS_EXT."""
        self.pasta = pasta
        os.makedirs(pasta, exist_ok=True)
        self.extras = extras or {}
        self.campos = CAMPOS_EXT if self.extras else CAMPOS
        self.csv = os.path.join(pasta, saida)
        self.erros = os.path.join(pasta, "erros.log")
        self.parar = os.path.join(AQUI, "PARAR")
        self.teste = os.path.abspath(pasta) != AQUI  # --dir diferente: amostras de codigo com prefixo teste_
        self.commit = subprocess.run(["git", "-C", LLAMA, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self._tm = None
        self._carregado = {}

    def log_erro(self, modelo, nivel, bench, msg):
        with open(self.erros, "a") as f: f.write(f"{agora()} {modelo} {nivel} {bench}: {msg}\n")
        print(f"ERRO {modelo} {nivel} {bench}: {msg[:2000]}", flush=True)

    def linhas(self, arquivo=None):
        """Linhas do CSV desta execucao (so as que batem com os extras kv e raciocinio) ou, com `arquivo`, todas as linhas daquele CSV da pasta."""
        caminho = os.path.join(self.pasta, arquivo) if arquivo else self.csv
        if not os.path.exists(caminho): return []
        todas = list(csv.DictReader(open(caminho)))
        return todas if arquivo else [r for r in todas if all(r.get(k) == str(v) for k, v in self.extras.items())]

    def feitos(self):
        return {(r["modelo"], r["nivel"], r["benchmark"]) for r in self.linhas()}

    def conhecido(self, modelo, bench, so_proprio=False):
        """True se o modelo ja tem alguma linha desta prova em resultados.csv ou no CSV desta execucao (prova e modelo nao sao novos). so_proprio: so o CSV desta execucao (raciocinio ligado e uma configuracao nova)."""
        nomes = {nome_csv(bench), bench}
        return any(r["modelo"] == modelo and r["benchmark"] in nomes for r in (self.linhas() if so_proprio else self.linhas("resultados.csv") + self.linhas()))

    def gravar(self, **linha):
        novo = not os.path.exists(self.csv)
        with open(self.csv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.campos)
            if novo: w.writeheader()
            w.writerow({**{c: "" for c in self.campos}, **self.extras, **linha, "commit_llama_cpp": self.commit, "data": agora()})
            f.flush(); os.fsync(f.fileno())

    def reusar(self, modelo, nivel, bench, origem="resultados.csv"):
        """Copia de `origem` a(s) linha(s) ja medidas com a mesma configuracao (ver REUSO). True se copiou."""
        if bench not in REUSO: return False
        achadas = [(r, novo) for velho, novo in REUSO[bench] for r in self.linhas(origem) if (r["modelo"], r["nivel"], r["benchmark"]) == (modelo, nivel, velho)]
        if len(achadas) < len(REUSO[bench]): return False
        for r, novo in achadas:
            r = {k: v for k, v in r.items() if k in self.campos}
            r["benchmark"] = novo
            with open(self.csv, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=self.campos)
                if f.tell() == 0: w.writeheader()
                w.writerow({**{c: "" for c in self.campos}, **r, **self.extras})
        print(f"reusa {modelo} {nivel} {bench}: linha ja medida em {origem} com a mesma configuracao", flush=True)
        return True

    def teste5(self):
        p = os.path.join(self.pasta, "logs", "teste5.json")
        return json.load(open(p)) if os.path.exists(p) else {}

    def gravar_teste5(self, chave, dados):
        t = self.teste5()
        t[chave] = {**dados, "data": agora()}
        os.makedirs(os.path.join(self.pasta, "logs"), exist_ok=True)
        p = os.path.join(self.pasta, "logs", "teste5.json")
        json.dump(t, open(p + ".tmp", "w"), indent=1, ensure_ascii=False)
        os.replace(p + ".tmp", p)

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


def log_servidor(modelo, nivel, kv=None):
    pasta = os.path.join(AQUI, "logs", "servidor")
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, f"{modelo}_{nivel}{'_kv' + kv if kv else ''}_{time.strftime('%Y%m%dT%H%M%S')}.log")


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


def mem_usada_mib():
    """MemTotal - MemAvailable (MiB). Na DGX Spark a memoria e unificada: inclui o que a GPU aloca."""
    d = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo") if l.split()[0].rstrip(":") in ("MemTotal", "MemAvailable")}
    return round((d["MemTotal"] - d["MemAvailable"]) / 1024)


def status_proc(pid):
    d = {}
    for l in open(f"/proc/{pid}/status"):
        if l.startswith(("VmRSS", "VmHWM")): d[l.split(":")[0]] = round(int(l.split()[1]) / 1024)
    return d


def kv_formula_mib(modelo, tokens, kv):
    """Etapa 3: tokens x camadas de atencao x cabecas KV x dim da cabeca x (bytes do K + bytes do V). None se nao der para ler o config."""
    try:
        cfg = json.load(open(os.path.join(MODELOS, modelo, "config.json")))
        cfg = cfg.get("text_config", cfg)
        camadas = sum(t == "full_attention" for t in cfg["layer_types"]) if cfg.get("layer_types") else cfg["num_hidden_layers"]
        d = cfg.get("head_dim") or cfg["hidden_size"] // cfg["num_attention_heads"]
        tk, tv = KV_TIPOS[kv]
        return round(tokens * camadas * cfg["num_key_value_heads"] * d * (BYTES_KV[tk] + BYTES_KV[tv]) / 2 ** 20, 1)
    except Exception: return None


class ServidorFalhou(RuntimeError): pass


class Sessao:
    """Um (modelo, nivel): carrega o hf ou sobe o llama-server so quando um benchmark precisa, e libera o outro.
    kv: None = servidor como nas medicoes antigas; "16"/"8"/"4"/"k4v8" = tipos do cache KV (liga flash attention) e registra a memoria em kv_memoria.csv."""
    def __init__(self, m, modelo, nivel, raciocinio, batch_hf=16, kv=None, ctx=32768, max_gen=2048, sistema=None):
        self.m, self.modelo, self.nivel, self.raciocinio, self.batch_hf = m, modelo, nivel, raciocinio, batch_hf
        self.kv, self.ctx, self.max_gen, self.sistema = kv, ctx, max_gen, sistema
        self._lm = self._srv = self._path = self._dtype = None
        self._mem_antes = None

    def path(self):
        if self._path is None: self._path = garantir_gguf(self.m, self.modelo, self.nivel)
        return self._path

    def hf(self, dtype="float16"):
        self.fechar_servidor()
        if self._lm is not None and self._dtype != dtype: self.fechar_hf()
        if self._lm is None:
            import torch
            from lm_eval.models.huggingface import HFLM
            self._lm = HFLM(pretrained=MODELOS, gguf_file=os.path.basename(self.path()), tokenizer=os.path.join(MODELOS, self.modelo), dtype=dtype, batch_size=self.batch_hf, device="cuda")
            self._dtype = dtype
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
            cmd = [os.path.join(BIN, "llama-server"), "-m", self.path(), "-ngl", "99", "-np", "8", "-c", str(self.ctx), "--host", "127.0.0.1", "--port", "8080"]
            if self.kv: cmd += ["-ctk", KV_TIPOS[self.kv][0], "-ctv", KV_TIPOS[self.kv][1], "-fa", "on"]  # V quantizado exige flash attention
            if not self.raciocinio: cmd += ["--chat-template-kwargs", '{"enable_thinking":false}']
            self._mem_antes = mem_usada_mib()
            self._srv = subprocess.Popen(cmd, stdout=open(log_servidor(self.modelo, self.nivel, self.kv), "w"), stderr=subprocess.STDOUT)
            try: esperar_servidor(self._srv)
            except RuntimeError as e: raise ServidorFalhou(str(e))
            if self.kv: self.registrar_memoria("pronto")
        return self._srv

    def registrar_memoria(self, momento):
        """kv_memoria.csv: cache KV pela formula da etapa 3, memoria usada da maquina e do processo, para conferir a formula."""
        arq = os.path.join(self.m.pasta, "kv_memoria.csv")
        campos = ["modelo", "nivel", "kv", "momento", "ctx_total", "kv_formula_mib", "gguf_mib", "mem_usada_mib", "mem_antes_do_servidor_mib", "rss_servidor_mib", "pico_rss_servidor_mib", "nvidia_smi", "data"]
        try: smi = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"], capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception: smi = ""
        p = status_proc(self._srv.pid) if self._srv is not None and self._srv.poll() is None else {}
        novo = not os.path.exists(arq)
        with open(arq, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            if novo: w.writeheader()
            w.writerow(dict(modelo=self.modelo, nivel=self.nivel, kv=self.kv, momento=momento, ctx_total=self.ctx, kv_formula_mib=kv_formula_mib(self.modelo, self.ctx, self.kv),
                            gguf_mib=round(os.path.getsize(self.path()) / 2 ** 20), mem_usada_mib=mem_usada_mib(), mem_antes_do_servidor_mib=self._mem_antes,
                            rss_servidor_mib=p.get("VmRSS", ""), pico_rss_servidor_mib=p.get("VmHWM", ""), nvidia_smi=smi, data=agora()))

    def fechar_servidor(self):
        if self.kv and self._srv is not None and self._srv.poll() is None:
            try: self.registrar_memoria("fim")
            except Exception: pass
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


def rodar_loglik(m, s, bench, limite, teste=0):
    """teste > 0: roda so `teste` exemplos, sem gravar nada, e devolve (acuracia, n)."""
    from lm_eval.loggers import EvaluationTracker
    cfg = LOGLIK[bench]
    if cfg.get("token") and not os.environ.get("HF_TOKEN"): raise RuntimeError("HF_TOKEN ausente no ambiente do job")
    task = cfg["task"]
    lm = s.hf(cfg.get("dtype", "float16"))
    m.preparar(task)
    tracker = None if teste else EvaluationTracker(output_path=amostra_dir(m, s, bench))
    t0 = time.perf_counter()
    limite = teste or limite
    sel = dict(limit=limite or None)
    if cfg.get("sorteio") and limite:  # sorteia `limite` questoes com seed 42 (as mesmas nos 3 modelos), em vez de pegar as primeiras
        total = len(m._carregado[task]["tasks"][task].eval_docs)
        sel = dict(samples={task: sorted(random.Random(42).sample(range(total), limite))})
    res = m.avaliar(task, model=lm, num_fewshot=cfg.get("fewshot"), log_samples=not teste, evaluation_tracker=tracker, **sel)
    tempo = time.perf_counter() - t0
    if not teste: salvar(tracker, res)
    if task == "mmlu":
        g = res["groups"]["mmlu"]
        n = sum(v["effective"] for v in res["n-samples"].values())
    else:
        g = res["results"][task]
        n = res["n-samples"][task]["effective"]
    if teste: return g["acc,none"], n
    m.gravar(modelo=s.modelo, nivel=s.nivel, benchmark=bench, n=n, acuracia=num(g["acc,none"]), erro_padrao=num(g["acc_stderr,none"]), tempo_s=round(tempo, 1))
    print(f"{bench} {s.modelo} {s.nivel}: n={n} acc={g['acc,none']:.4f} em {tempo:.0f} s", flush=True)


def stats_proxy(log):
    regs = [json.loads(l) for l in open(log)] if os.path.exists(log) else []
    ok = [r for r in regs if "completion_tokens" in r]
    return round(sum(r["completion_tokens"] for r in ok) / max(len(ok), 1), 1), sum(r["finish_reason"] == "length" for r in ok)


def rodar_gerativo(m, s, bench, limite, teste=0):
    """teste > 0: roda so `teste` exemplos, sem gravar nada, e devolve (valor principal, n)."""
    from lm_eval.loggers import EvaluationTracker
    task = GERATIVO[bench]["task"]
    s.servidor()
    saida = os.path.join(AQUI, "logs", "teste5", f"{s.modelo}_{bench}") if teste else amostra_dir(m, s, bench)
    os.makedirs(saida, exist_ok=True)
    proxy_log = os.path.join(saida, "proxy.jsonl")
    proxy = subprocess.Popen([VENV_PY, PROXY, "http://127.0.0.1:8080", proxy_log, "8081"])
    try:
        esperar_porta(proxy)
        m.preparar(task)
        tracker = None if teste else EvaluationTracker(output_path=saida)
        extra = dict(system_instruction=s.sistema) if s.sistema else {}
        t0 = time.perf_counter()
        res = m.avaliar(task, model="local-chat-completions",
                        model_args="model=qwen,base_url=http://127.0.0.1:8081/v1/chat/completions,num_concurrent=8,max_retries=1,tokenized_requests=False,timeout=3600",
                        limit=teste or limite or None, apply_chat_template=True, fewshot_as_multiturn=True, gen_kwargs=f"temperature=0,max_gen_toks={s.max_gen}",
                        log_samples=not teste, evaluation_tracker=tracker, **extra)
        tempo = time.perf_counter() - t0
        if not teste:
            salvar(tracker, res)
            if s.sistema: open(os.path.join(saida, "prompt_sistema.txt"), "w").write(s.sistema + "\n")
    finally:
        matar(proxy)
    tokens, cortadas = stats_proxy(proxy_log)
    r = res["results"][task]
    n = res["n-samples"][task]["effective"]
    if teste:
        chave = {"gsm8k": "exact_match,flexible-extract", "math500": "math_verify,none", "wmt24": "chrf,none"}[bench]
        return r[chave], n
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


def rodar_letra(m, s, bench, limite, teste=0):
    """MMLU/OAB por geracao da letra (letra.py). teste > 0 nao e usado: a validacao e o proprio mmlu_letra/oab_letra do 7B f16."""
    import letra
    s.servidor()
    itens, tempo = letra.avaliar(bench, limite)
    saida = amostra_dir(m, s, bench)
    os.makedirs(saida, exist_ok=True)
    with open(os.path.join(saida, "amostras.jsonl"), "w") as f: f.write("\n".join(json.dumps(x, ensure_ascii=False) for x in itens) + "\n")
    n = len(itens)
    acc = sum(x["acertou"] for x in itens) / n
    sem_letra = sum(x["letra"] is None for x in itens)  # na coluna `cortadas`: respostas em que nao havia letra A-D
    m.gravar(modelo=s.modelo, nivel=s.nivel, benchmark=bench, n=n, acuracia=num(acc), erro_padrao=erro_binomial(acc, n), tempo_s=round(tempo, 1),
             tokens_por_resposta=round(sum(x["tokens"] for x in itens) / n, 2), cortadas=sem_letra)
    print(f"{bench} {s.modelo} {s.nivel}: n={n} acc={acc:.4f} sem letra={sem_letra} em {tempo:.0f} s", flush=True)


def rodar_codigo(m, s, bench, limite, teste=0):
    """Gera as solucoes (nao executa codigo). A pontuacao e o CSV vem depois: pontuar_codigo.py (job isolado) e --ingerir-codigo.
    teste > 0: gera `teste` solucoes, nao grava e devolve quantas sao sintaxe Python valida (ast.parse; nada e executado)."""
    import codigo
    if teste:
        s.servidor()
        saidas, _ = codigo.gerar(bench, teste)
        def valido(c):
            try: ast.parse(c); return bool(c.strip())
            except SyntaxError: return False
        return sum(valido(x["solution"]) for x in saidas), len(saidas)
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


def testar(m, s, bench):
    """Prova ou modelo novos: 5 exemplos antes da medicao. Passa se a acuracia for > 0 (a metrica leu o formato da resposta); se der 0 em 5, tenta 20 antes de reprovar.
    Codigo: passa se pelo menos uma das solucoes e Python sintaticamente valido (a pontuacao so existe no job isolado). Devolve True/False e registra em logs/teste5.json."""
    chave = f"{s.modelo}|{bench}" + ("|raciocinio" if s.raciocinio else "")
    anterior = m.teste5().get(chave)
    if anterior: return anterior["ok"]
    try:
        for k in (5, 20):
            if bench in LOGLIK: valor, n = rodar_loglik(m, s, bench, 0, teste=k)
            elif bench in GERATIVO: valor, n = rodar_gerativo(m, s, bench, 0, teste=k)
            else: valor, n = rodar_codigo(m, s, bench, 0, teste=k)
            print(f"teste de {k} exemplos {s.modelo} {s.nivel} {bench}: valor={valor} n={n}", flush=True)
            if valor > 0: break
        ok, motivo = bool(valor > 0), "" if valor > 0 else f"acuracia 0 em {n} exemplos: a metrica nao leu o formato da resposta ou o modelo nao responde a prova"
    except ServidorFalhou: raise
    except Exception:
        ok, motivo, valor, n = False, "erro no teste: " + traceback.format_exc()[-1500:], None, None
        s.fechar_servidor()
    m.gravar_teste5(chave, dict(ok=bool(ok), valor=None if valor is None else float(valor), n=None if n is None else int(n), nivel=s.nivel, motivo=motivo))
    if not ok: m.log_erro(s.modelo, s.nivel, bench, f"teste de 5 exemplos reprovou, prova pulada: {motivo}")
    return ok


def main():
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo")
    ap.add_argument("--niveis", nargs="+", default=["f16", "q8_0", "q4_k_m"], choices=list(TIPO))
    ap.add_argument("--benchmarks", nargs="+", default=[b for b in ORDEM if b != "mmlu_completo"], choices=ORDEM)
    ap.add_argument("--limites", nargs="*", default=[], help="nome=N (0 = completo); padrao: mmlu=25, o resto completo")
    ap.add_argument("--sem-raciocinio", action="store_true", help="(padrao; mantido por compatibilidade) raciocinio desligado: enable_thinking=false nos gerativos")
    ap.add_argument("--raciocinio-ligado", action="store_true", help="raciocinio ligado, 4096 tokens por resposta, contexto 65536; grava em raciocinio.csv")
    ap.add_argument("--kv", choices=list(KV_TIPOS), help="tipo do cache KV do llama-server (16=f16, 8=q8_0, 4=q4_0, k4v8=K q4_0 e V q8_0); grava em kv.csv")
    ap.add_argument("--saida", default="resultados.csv", help="CSV de saida; kv.csv e raciocinio.csv levam as colunas kv e raciocinio")
    ap.add_argument("--reusar-de", help="copia de resultados.csv as linhas (gsm8k, math500, mmlu) ja medidas com a mesma configuracao, em vez de repetir")
    ap.add_argument("--sistema", help="prompt de sistema nos gerativos (lm-eval system_instruction)")
    ap.add_argument("--max-gen", type=int, help="max_gen_toks dos gerativos (padrao 2048; 4096 com raciocinio ligado)")
    ap.add_argument("--batch-hf", type=int, default=16, help="batch_size do HFLM (log-prob); reduzir para modelos muito grandes")
    ap.add_argument("--respeitar-etapa1", action="store_true", help="pula os benchmarks marcados como pulados em etapa1.json")
    ap.add_argument("--ingerir-codigo", action="store_true")
    ap.add_argument("--dir", default=AQUI)
    a = ap.parse_args()
    if a.raciocinio_ligado and a.sem_raciocinio: ap.error("--raciocinio-ligado e --sem-raciocinio juntos")
    extras = {"kv": a.kv or "16", "raciocinio": "ligado" if a.raciocinio_ligado else "desligado"} if a.saida != "resultados.csv" else None
    if a.saida != "resultados.csv" and (a.saida.startswith("resultados") or a.saida not in ("kv.csv", "raciocinio.csv")): ap.error("--saida: resultados.csv, kv.csv ou raciocinio.csv")
    m = Medicao(a.dir, a.saida, extras)
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
    falhou = servidor_falhou = False
    ligado = a.raciocinio_ligado
    for nivel in a.niveis:
        s = Sessao(m, a.modelo, nivel, ligado, a.batch_hf, kv=a.kv, ctx=65536 if ligado else 32768, max_gen=a.max_gen or (4096 if ligado else 2048), sistema=a.sistema)
        try:
            for bench in ativos:
                if (a.modelo, nivel, nome_csv(bench)) in m.feitos():
                    print(f"pula {a.modelo} {nivel} {bench}: ja no CSV", flush=True)
                    continue
                if os.path.exists(m.parar): sys.exit(3)
                if a.reusar_de and not ligado and (a.kv or "16") == "16" and m.reusar(a.modelo, nivel, bench, a.reusar_de): continue
                print(f"##### {a.modelo} {nivel} {bench} ({agora()})", flush=True)
                limite = limites.get(bench, {**LOGLIK, **LETRA}.get(bench, {}).get("limite", 0))
                try:
                    if bench not in LETRA and not m.conhecido(a.modelo, bench, ligado) and not testar(m, s, bench):
                        print(f"pula {a.modelo} {nivel} {bench}: teste de 5 exemplos reprovou (ver erros.log)", flush=True)
                        continue
                    if bench in LOGLIK: rodar_loglik(m, s, bench, limite)
                    elif bench in GERATIVO: rodar_gerativo(m, s, bench, limite)
                    elif bench in LETRA: rodar_letra(m, s, bench, limite)
                    else: rodar_codigo(m, s, bench, limite)
                except ServidorFalhou:
                    falhou = servidor_falhou = True
                    m.log_erro(a.modelo, nivel, bench, f"llama-server nao subiu (kv={a.kv}): " + traceback.format_exc()[-1500:])
                    s.fechar_servidor()
                    break
                except Exception:
                    falhou = True
                    m.log_erro(a.modelo, nivel, bench, traceback.format_exc())
                    s.fechar_servidor()
        finally:
            s.fechar()
    sys.exit(4 if servidor_falhou else 1 if falhou else 0)


if __name__ == "__main__":
    main()
