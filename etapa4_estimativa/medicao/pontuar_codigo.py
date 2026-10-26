"""Roda DENTRO do conteiner isolado (so /work montado, sem a home). Pontua com o evalplus as solucoes de /work/samples.
Completa com solucao vazia os problemas nao gerados (o evalplus exige todos) e conta so os gerados. Uso: pontuar_codigo.py [--teste]  (--teste = so os arquivos teste_*)"""
import glob, json, os, subprocess, sys

TESTE = "--teste" in sys.argv
os.makedirs("/work/resultados_codigo", exist_ok=True)
os.makedirs("/work/tmp", exist_ok=True)
import evalplus.data as ed

PROBLEMAS = {"humaneval": list(ed.get_human_eval_plus()), "mbpp": list(ed.get_mbpp_plus())}
for f in sorted(glob.glob("/work/samples/*.jsonl")):
    nome = os.path.basename(f)[:-len(".jsonl")]
    if nome.startswith("teste_") != TESTE: continue
    saida = f"/work/resultados_codigo/{nome}.json"
    if os.path.exists(saida):
        print(f"pula {nome}: ja pontuado", flush=True)
        continue
    bench = "humaneval" if nome.endswith("__humaneval") else "mbpp"
    gerados = [json.loads(l) for l in open(f)]
    ids = [g["task_id"] for g in gerados]
    extra = [{"task_id": t, "solution": "pass"} for t in PROBLEMAS[bench] if t not in set(ids)]
    completo = f"/work/tmp/{nome}.jsonl"
    with open(completo, "w") as fo:
        fo.write("\n".join(json.dumps({"task_id": g["task_id"], "solution": g["solution"]}) for g in gerados + extra) + "\n")
    print(f"##### {nome}: {len(ids)} gerados + {len(extra)} vazios", flush=True)
    subprocess.run([sys.executable, "-m", "evalplus.evaluate", "--dataset", bench, "--samples", completo], check=True)
    res = json.load(open(f"/work/tmp/{nome}_eval_results.json"))["eval"]
    tarefas = {t: [int(res[t][0]["base_status"] == "pass"), int(res[t][0]["base_status"] == "pass" and res[t][0]["plus_status"] == "pass")] for t in ids}
    r = {"n": len(ids), "base": sum(v[0] for v in tarefas.values()), "plus": sum(v[1] for v in tarefas.values()), "tarefas": tarefas}
    json.dump(r, open(saida, "w"))
    print(f"{nome}: base {r['base']}/{r['n']}, plus {r['plus']}/{r['n']}", flush=True)
