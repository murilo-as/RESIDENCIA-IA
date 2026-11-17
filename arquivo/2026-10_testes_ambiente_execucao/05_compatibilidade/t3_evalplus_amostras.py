"""Roda DENTRO do conteiner sem a home. Fase 'completar': o evalplus exige amostras de todos os problemas, entao completa com solucao vazia ("pass"). Fase 'resumir': pass@1 so dos task_id gerados."""
import json, sys

FASE = sys.argv[1]
NOMES = {"humaneval": "get_human_eval_plus", "mbpp": "get_mbpp_plus"}
if FASE == "completar":
    import evalplus.data as ed
    for nome, fn in NOMES.items():
        todos = list(getattr(ed, fn)())
        reais = [json.loads(l) for l in open(f"/work/samples/{nome}.jsonl")]
        vistos = {a["task_id"] for a in reais}
        extra = [{"task_id": t, "solution": "pass"} for t in todos if t not in vistos]
        with open(f"/work/samples/{nome}_completo.jsonl", "w") as f:
            f.write("\n".join(json.dumps(x) for x in reais + extra) + "\n")
        print(f"{nome}: {len(reais)} reais + {len(extra)} vazias = {len(reais) + len(extra)} (problemas: {len(todos)})")
else:
    for nome in NOMES:
        ids = [json.loads(l)["task_id"] for l in open(f"/work/samples/{nome}.jsonl")]
        res = json.load(open(f"/work/samples/{nome}_completo_eval_results.json"))["eval"]
        base = sum(res[t][0]["base_status"] == "pass" for t in ids)
        plus = sum(res[t][0]["base_status"] == "pass" and res[t][0]["plus_status"] == "pass" for t in ids)
        print(f"{nome}: {len(ids)} problemas gerados; pass@1 base {base}/{len(ids)} = {base / len(ids):.2f}; pass@1 base+plus {plus}/{len(ids)} = {plus / len(ids):.2f}")
        for t in ids: print(f"  {t}: base={res[t][0]['base_status']} plus={res[t][0]['plus_status']}")
