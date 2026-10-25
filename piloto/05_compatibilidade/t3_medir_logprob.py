"""T3 parte 3 (log-prob): 20 exemplos por task com o Qwen2.5-7B Q4_K_M (hf, gguf_file, float16, batch 16, seed 42). Uso: <task> [<task> ...]. Mede carga, montagem e avaliacao, e tokens de contexto por exemplo."""
import json, os, sys, time, traceback
import torch
from lm_eval import simple_evaluate
from lm_eval.models.huggingface import HFLM
from lm_eval.tasks import TaskManager

AQUI = os.path.dirname(os.path.abspath(__file__))
M = "/beegfs/home/user_muriloalves/work/models"
OUT = os.path.join(AQUI, "..", "resultados", "t3_logprob")
os.makedirs(OUT, exist_ok=True)


class Pronto:
    def __init__(self, tm, carregado): self._tm, self._c = tm, carregado
    def load(self, tasks): return self._c
    def __getattr__(self, k): return getattr(self._tm, k)


t0 = time.perf_counter()
lm = HFLM(pretrained=M, gguf_file="qwen2.5-7b-instruct-q4_k_m.gguf", tokenizer=f"{M}/Qwen2.5-7B-Instruct", dtype="float16", batch_size=16, device="cuda")
torch.cuda.synchronize()
print(f"carga do modelo: {time.perf_counter() - t0:.1f} s")
tm = TaskManager(include_path=os.path.join(AQUI, "tasks"))
for t in sys.argv[1:]:
    print(f"##### {t}")
    try:
        t0 = time.perf_counter()
        carregado = tm.load([t])
        t_tarefas = time.perf_counter() - t0
        t0 = time.perf_counter()
        res = simple_evaluate(model=lm, tasks=[t], num_fewshot=5 if t.startswith("mmlu") else None, limit=20, log_samples=True,
                              task_manager=Pronto(tm, carregado), random_seed=42, numpy_random_seed=42, torch_random_seed=42, fewshot_random_seed=42)
        t_aval = time.perf_counter() - t0
        n = res["n-samples"][t]["effective"]
        ctx = [len(lm.tok_encode(a["arguments"][0][0])) for a in res["samples"][t]]
        acc = res["results"][t]
        r = {"task": t, "n": n, "montar_tarefas_s": t_tarefas, "avaliacao_s": t_aval, "s_por_exemplo": t_aval / n,
             "tokens_contexto_media": sum(ctx) / len(ctx), "tokens_contexto_max": max(ctx), "acc": acc.get("acc,none"), "stderr": acc.get("acc_stderr,none")}
        json.dump(r, open(os.path.join(OUT, f"{t}.json"), "w"), indent=1)
        print(json.dumps(r, indent=1))
    except Exception:
        print("FALHOU:\n" + traceback.format_exc())
