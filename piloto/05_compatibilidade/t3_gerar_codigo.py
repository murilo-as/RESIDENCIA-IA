"""T3 parte 3 (codigo): gera 20 solucoes de HumanEval+ e 20 de MBPP+ pelo llama-server (uma requisicao por vez) e grava os jsonl para o evalplus. Nao executa codigo."""
import json, re, sys, time, urllib.request
from datasets import load_dataset

URL = "http://127.0.0.1:8080/v1/chat/completions"
STAGE = "/beegfs/home/user_muriloalves/work/tmp_codigo/samples"
STATS = sys.argv[1]
N = 20


def chat(msg):
    corpo = {"model": "qwen", "messages": [{"role": "user", "content": msg}], "temperature": 0, "max_tokens": 1024}
    req = urllib.request.Request(URL, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    r = json.load(urllib.request.urlopen(req, timeout=900))
    return r["choices"][0]["message"]["content"], r["usage"]["completion_tokens"], r["choices"][0]["finish_reason"], time.perf_counter() - t0


def codigo(texto):
    blocos = re.findall(r"```(?:python)?\n(.*?)```", texto, re.S)
    return max(blocos, key=len) if blocos else texto


stats = {}
for nome, ds, mk, tid in [("humaneval", "evalplus/humanevalplus", lambda d: "Complete the following Python function. Reply with the complete function in one ```python code block.\n\n```python\n" + d["prompt"] + "```", lambda d: d["task_id"]),
                          ("mbpp", "evalplus/mbppplus", lambda d: d["prompt"] + "\nYour code should pass these tests:\n" + "\n".join(d["test_list"][:3]) + "\nReply with the complete code in one ```python code block.", lambda d: "Mbpp/" + str(d["task_id"]))]:
    dados = load_dataset(ds)["test"]
    linhas, medidas = [], []
    for d in list(dados)[:N]:
        texto, ntok, fim, dt = chat(mk(d))
        sol = codigo(texto)
        if nome == "humaneval" and f"def {d['entry_point']}" not in sol: sol = d["prompt"] + sol
        linhas.append({"task_id": tid(d), "solution": sol})
        medidas.append({"task_id": tid(d), "segundos": dt, "tokens": ntok, "finish_reason": fim})
        print(f"{nome} {tid(d)}: {dt:.1f} s, {ntok} tokens, {fim}")
    with open(f"{STAGE}/{nome}.jsonl", "w") as f:
        f.write("\n".join(json.dumps(x) for x in linhas) + "\n")
    tok = [m["tokens"] for m in medidas]
    stats[nome] = {"n": len(medidas), "s_por_exemplo": sum(m["segundos"] for m in medidas) / len(medidas), "tokens_media": sum(tok) / len(tok),
                   "tokens_max": max(tok), "cortadas": sum(m["finish_reason"] == "length" for m in medidas), "medidas": medidas}
    print(f"== {nome}: {stats[nome]['s_por_exemplo']:.2f} s/exemplo, tokens media {stats[nome]['tokens_media']:.1f} max {stats[nome]['tokens_max']}, cortadas {stats[nome]['cortadas']}")
json.dump(stats, open(STATS, "w"), indent=1)
