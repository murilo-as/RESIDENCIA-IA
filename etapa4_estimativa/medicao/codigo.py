"""Geracao de solucoes para HumanEval+ e MBPP+ pelo llama-server (8 requisicoes em paralelo). Nao executa codigo: a pontuacao e feita por pontuar_codigo.py em job isolado."""
import json, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "http://127.0.0.1:8080/v1/chat/completions"
DATASETS = {"humaneval": "evalplus/humanevalplus", "mbpp": "evalplus/mbppplus"}


def prompt(bench, d):
    if bench == "humaneval":
        return "Complete the following Python function. Reply with the complete function in one ```python code block.\n\n```python\n" + d["prompt"] + "```"
    return d["prompt"] + "\nYour code should pass these tests:\n" + "\n".join(d["test_list"][:3]) + "\nReply with the complete code in one ```python code block."


def task_id(bench, d): return d["task_id"] if bench == "humaneval" else "Mbpp/" + str(d["task_id"])


def extrair_codigo(texto):
    blocos = re.findall(r"```(?:python)?\n(.*?)```", texto, re.S)
    return max(blocos, key=len) if blocos else texto


def conversar(msg):
    corpo = {"model": "qwen", "messages": [{"role": "user", "content": msg}], "temperature": 0, "max_tokens": 1024}
    req = urllib.request.Request(URL, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    r = json.load(urllib.request.urlopen(req, timeout=1800))
    return (r["choices"][0]["message"]["content"] or ""), r["usage"]["completion_tokens"], r["choices"][0]["finish_reason"], time.perf_counter() - t0


def um(bench, d):
    texto, ntok, fim, dt = conversar(prompt(bench, d))
    sol = extrair_codigo(texto)
    if bench == "humaneval" and f"def {d['entry_point']}" not in sol: sol = d["prompt"] + sol
    return {"task_id": task_id(bench, d), "solution": sol, "tokens": ntok, "finish_reason": fim, "segundos": dt}


def gerar(bench, limite=0, trabalhadores=8):
    """Devolve (lista de dicts por problema, segundos totais)."""
    from datasets import load_dataset
    problemas = list(load_dataset(DATASETS[bench])["test"])
    if limite: problemas = problemas[:limite]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(trabalhadores) as ex:
        saidas = list(ex.map(lambda d: um(bench, d), problemas))
    return saidas, time.perf_counter() - t0
