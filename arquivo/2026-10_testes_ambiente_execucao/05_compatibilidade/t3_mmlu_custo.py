"""T3: custo do MMLU 5-shot (hf, gguf_file, float16, batch 16, seed 42), com carga, montagem das tarefas e avaliacao medidas separadas. Uso: <tag> <arquivo.gguf> <pasta_tokenizer> <limit>."""
import json, os, sys, time
import torch
from lm_eval import simple_evaluate
from lm_eval.models.huggingface import HFLM
from lm_eval.tasks import TaskManager

tag, GGUF, tok, limit = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
M = "/beegfs/home/user_muriloalves/work/models"
OUT = f"/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/resultados/t3_{tag}_lim{limit}"
os.makedirs(OUT, exist_ok=True)


class Pronto:
    """TaskManager que devolve as tarefas ja montadas, para medir a montagem separada da avaliacao."""
    def __init__(self, tm, carregado): self._tm, self._c = tm, carregado
    def load(self, tasks): return self._c
    def __getattr__(self, k): return getattr(self._tm, k)


t0 = time.perf_counter()
lm = HFLM(pretrained=M, gguf_file=GGUF, tokenizer=f"{M}/{tok}", dtype="float16", batch_size=16, device="cuda")
torch.cuda.synchronize()
t_carga = time.perf_counter() - t0
t0 = time.perf_counter()
tm = TaskManager()
carregado = tm.load(["mmlu"])
t_tarefas = time.perf_counter() - t0
t0 = time.perf_counter()
res = simple_evaluate(model=lm, tasks=["mmlu"], num_fewshot=5, limit=limit, log_samples=False, task_manager=Pronto(tm, carregado),
                      random_seed=42, numpy_random_seed=42, torch_random_seed=42, fewshot_random_seed=42)
t_aval = time.perf_counter() - t0
n = sum(v["effective"] for k, v in res["n-samples"].items())
mmlu = res["groups"]["mmlu"]
r = {"tag": tag, "limit": limit, "n_questoes": n, "n_pedidos_loglik": 4 * n, "carga_s": t_carga, "montar_tarefas_s": t_tarefas,
     "avaliacao_s": t_aval, "mmlu_acc": mmlu["acc,none"], "mmlu_stderr": mmlu["acc_stderr,none"], "s_por_questao_aval": t_aval / n}
json.dump(r, open(os.path.join(OUT, "tempos.json"), "w"), indent=1)
print(json.dumps(r, indent=1))
