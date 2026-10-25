"""T2: carga do GGUF Q4_K_M com transformers (float16) e MMLU 5-shot --limit 2 (seed 42, batch 16). Uso: <tag> <arquivo.gguf> <pasta_tokenizer>."""
import collections, gc, json, os, sys, time, traceback
import torch
from transformers import AutoModelForCausalLM

tag, GGUF, tok = sys.argv[1:4]
M = "/beegfs/home/user_muriloalves/work/models"
OUT = f"/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/resultados/t2_{tag}_fp16_bs16"
os.makedirs(OUT, exist_ok=True)
status = {"modelo": tag, "gguf": GGUF}

print(f"##### {tag}: carga com transformers (gguf_file, dtype=float16)")
try:
    t0 = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(M, gguf_file=GGUF, dtype=torch.float16, device_map="cuda")
    torch.cuda.synchronize()
    status["carga_s"] = time.perf_counter() - t0
    por_dtype = collections.defaultdict(lambda: [0, 0])
    for p in model.parameters():
        por_dtype[str(p.dtype)][0] += p.numel()
        por_dtype[str(p.dtype)][1] += p.numel() * p.element_size()
    status["params_gib"] = sum(v[1] for v in por_dtype.values()) / 2**30
    status["gguf_gib"] = os.path.getsize(os.path.join(M, GGUF)) / 2**30
    status["classe"] = type(model).__name__
    status["model_type"] = model.config.model_type
    status["architectures"] = model.config.architectures
    print("carregou: sim")
    for k, (n, b) in por_dtype.items(): print(f"  {k}: {n} parametros, {b / 2**30:.3f} GiB")
    print(f"GiB dos parametros: {status['params_gib']:.3f}  (arquivo GGUF: {status['gguf_gib']:.3f} GiB)")
    print(f"tempo de carga: {status['carga_s']:.1f} s")
    print(f"classe: {status['classe']}  model_type: {status['model_type']}  config.architectures: {status['architectures']}")
    del model; gc.collect(); torch.cuda.empty_cache()
except Exception:
    status["carregou"] = False
    status["erro"] = traceback.format_exc()
    print("carregou: NAO\n" + status["erro"])
    json.dump(status, open(os.path.join(OUT, "status.json"), "w"), indent=1)
    sys.exit(0)

status["carregou"] = True
print(f"##### {tag}: MMLU 5-shot --limit 2 --seed 42 --log_samples, batch_size=16")
try:
    from lm_eval import simple_evaluate
    from lm_eval.loggers import EvaluationTracker
    from lm_eval.models.huggingface import HFLM
    from lm_eval.utils import make_table

    t0 = time.perf_counter()
    lm = HFLM(pretrained=M, gguf_file=GGUF, tokenizer=f"{M}/{tok}", dtype="float16", batch_size=16, device="cuda")
    torch.cuda.synchronize()
    status["carga_hflm_s"] = time.perf_counter() - t0
    tracker = EvaluationTracker(output_path=OUT)
    t0 = time.perf_counter()
    res = simple_evaluate(model=lm, tasks=["mmlu"], num_fewshot=5, limit=2, log_samples=True, evaluation_tracker=tracker,
                          random_seed=42, numpy_random_seed=42, torch_random_seed=42, fewshot_random_seed=42)
    status["avaliacao_s"] = time.perf_counter() - t0
    samples = res.pop("samples")
    tracker.save_results_aggregated(results=res, samples=samples)
    for t in res["configs"]: tracker.save_results_samples(task_name=t, samples=samples[t])
    print(make_table(res, "groups"))
    mmlu = res["groups"]["mmlu"]
    status["mmlu_acc"], status["mmlu_stderr"] = mmlu["acc,none"], mmlu["acc_stderr,none"]
    print(f"mmlu acc: {status['mmlu_acc']:.4f} +- {status['mmlu_stderr']:.4f}")
    print(f"tempo de carregamento (HFLM): {status['carga_hflm_s']:.1f} s")
    print(f"tempo de avaliacao (simple_evaluate, inclui montar as tarefas): {status['avaliacao_s']:.1f} s")
except Exception:
    status["erro_mmlu"] = traceback.format_exc()
    print("MMLU falhou:\n" + status["erro_mmlu"])
json.dump(status, open(os.path.join(OUT, "status.json"), "w"), indent=1)
