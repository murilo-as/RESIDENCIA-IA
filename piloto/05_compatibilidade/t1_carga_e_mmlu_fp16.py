"""T1: carrega o GGUF Q4_K_M com transformers (float16), mede memoria e tempo, e roda MMLU 5-shot (--limit 10, seed 42, batch 16) separando carga e avaliacao."""
import collections, gc, json, os, time
import torch
from transformers import AutoModelForCausalLM

M = "/beegfs/home/user_muriloalves/work/models"
GGUF = "qwen2.5-7b-instruct-q4_k_m.gguf"
OUT = "/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/resultados/t1_gguf_q4km_fp16_bs16"

print("##### Parte 1: carga com transformers (gguf_file, dtype=float16)")
t0 = time.perf_counter()
model = AutoModelForCausalLM.from_pretrained(M, gguf_file=GGUF, dtype=torch.float16, device_map="cuda")
torch.cuda.synchronize()
t_carga1 = time.perf_counter() - t0
por_dtype = collections.defaultdict(lambda: [0, 0])
for p in model.parameters():
    por_dtype[str(p.dtype)][0] += p.numel()
    por_dtype[str(p.dtype)][1] += p.numel() * p.element_size()
total = sum(v[1] for v in por_dtype.values())
gguf_bytes = os.path.getsize(os.path.join(M, GGUF))
print(f"model.dtype: {model.dtype}")
for k, (n, b) in por_dtype.items(): print(f"  {k}: {n} parametros, {b / 2**30:.3f} GiB")
print(f"soma dos bytes dos parametros: {total / 2**30:.3f} GiB")
print(f"arquivo GGUF: {gguf_bytes / 2**30:.3f} GiB ({gguf_bytes} bytes)")
print(f"razao parametros/GGUF: {total / gguf_bytes:.2f}")
print(f"cuda memory_allocated: {torch.cuda.memory_allocated() / 2**30:.3f} GiB")
print(f"tempo de carregamento: {t_carga1:.1f} s")
del model; gc.collect(); torch.cuda.empty_cache()

print("##### Parte 2: MMLU 5-shot --limit 10 --seed 42 --log_samples, dtype=float16, batch_size=16")
from lm_eval import simple_evaluate
from lm_eval.loggers import EvaluationTracker
from lm_eval.models.huggingface import HFLM
from lm_eval.utils import handle_non_serializable, make_table

t0 = time.perf_counter()
lm = HFLM(pretrained=M, gguf_file=GGUF, tokenizer=M + "/Qwen2.5-7B-Instruct", dtype="float16", batch_size=16, device="cuda")
torch.cuda.synchronize()
t_carga2 = time.perf_counter() - t0
tracker = EvaluationTracker(output_path=OUT)
t0 = time.perf_counter()
res = simple_evaluate(model=lm, tasks=["mmlu"], num_fewshot=5, limit=10, log_samples=True, evaluation_tracker=tracker,
                      random_seed=42, numpy_random_seed=42, torch_random_seed=42, fewshot_random_seed=42)
t_aval = time.perf_counter() - t0
samples = res.pop("samples")
tracker.save_results_aggregated(results=res, samples=samples)
for t in res["configs"]: tracker.save_results_samples(task_name=t, samples=samples[t])
print(make_table(res))
print(make_table(res, "groups"))
mmlu = res["groups"]["mmlu"]
print(f"mmlu acc: {mmlu['acc,none']:.4f} +- {mmlu['acc_stderr,none']:.4f}")
print(f"tempo de carregamento (HFLM): {t_carga2:.1f} s")
print(f"tempo de avaliacao (simple_evaluate, inclui montar as tarefas): {t_aval:.1f} s")
os.makedirs(OUT, exist_ok=True)
json.dump({"mmlu_acc": mmlu["acc,none"], "mmlu_stderr": mmlu["acc_stderr,none"], "carga_s": t_carga2, "avaliacao_s": t_aval,
           "carga_parte1_s": t_carga1, "params_gib": total / 2**30, "gguf_gib": gguf_bytes / 2**30}, open(os.path.join(OUT, "tempos.json"), "w"), indent=1)
