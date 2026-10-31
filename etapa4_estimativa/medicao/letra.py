"""Multipla escolha por geracao da letra (mmlu_letra, oab_letra), pelo llama-server ja no ar: o prompt tem instrucao em portugues e 5 exemplos resolvidos,
o modelo responde so a letra (temperatura 0, max 4 tokens) e a letra e extraida da resposta. Usa as mesmas questoes do log-prob:
MMLU = as primeiras `limite` do teste de cada assunto (como o lm-eval --limit) com os 5 primeiros do dev do assunto como exemplos; OAB = as 2205 validas, exemplos fixos da tarefa oab_exams_5shot."""
import importlib.util, json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
URL = "http://127.0.0.1:8080/v1/chat/completions"
LETRAS = "ABCD"
INSTRUCAO_MMLU = "As perguntas a seguir são de múltipla escolha (em inglês) sobre {assunto}. Escolha a alternativa correta e responda apenas com a letra (A, B, C ou D).\n\n"
INSTRUCAO_OAB = "As questões a seguir são do Exame de Ordem da OAB (primeira fase). Escolha a alternativa correta e responda apenas com a letra (A, B, C ou D).\n\n"


def bloco(pergunta, alternativas):
    return f"Pergunta: {pergunta.strip()}\n" + "\n".join(f"{l}. {t}" for l, t in zip(LETRAS, alternativas)) + "\nResposta:"


def montar(instrucao, exemplos, pergunta, alternativas):
    """Mensagens do chat: instrucao no sistema, cada exemplo resolvido como turno usuario/assistente (a resposta e so a letra) e, por fim, a pergunta.
    exemplos: lista de (pergunta, alternativas, letra)."""
    msgs = [{"role": "system", "content": instrucao.strip()}]
    for p, alt, letra in exemplos: msgs += [{"role": "user", "content": bloco(p, alt)}, {"role": "assistant", "content": letra}]
    return msgs + [{"role": "user", "content": bloco(pergunta, alternativas)}]


def itens_mmlu(limite):
    from datasets import load_dataset
    cache = os.path.join(os.environ.get("HF_HOME", ""), "datasets", "cais___mmlu")
    itens = []
    for assunto in sorted(d for d in os.listdir(cache) if os.path.isdir(os.path.join(cache, d))):
        ds = load_dataset("cais/mmlu", assunto)
        exemplos = [(d["question"], d["choices"], LETRAS[d["answer"]]) for d in list(ds["dev"])[:5]]
        teste = list(ds["test"])[:limite] if limite else list(ds["test"])
        instr = INSTRUCAO_MMLU.format(assunto=assunto.replace("_", " "))
        itens += [{"id": f"{assunto}/{i}", "mensagens": montar(instr, exemplos, d["question"], d["choices"]), "gold": LETRAS[d["answer"]]} for i, d in enumerate(teste)]
    return itens


def itens_oab(limite):
    from datasets import load_dataset
    spec = importlib.util.spec_from_file_location("oab_utils", os.path.join(AQUI, "tasks", "oab_exams_5shot", "utils.py"))
    u = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(u)
    ds = load_dataset("eduagarcia/oab_exams", split="train")
    exemplos = [(ds[i]["question"], ds[i]["choices"]["text"], ds[i]["answerKey"]) for i in u._exemplos(ds)]
    fora = set(u._exemplos(ds))
    docs = [(i, ds[i]) for i in u._validas(ds) if i not in fora]  # as mesmas 2205 do log-prob
    if limite: docs = docs[:limite]
    return [{"id": f"oab/{i}", "mensagens": montar(INSTRUCAO_OAB, exemplos, d["question"], d["choices"]["text"]), "gold": d["answerKey"]} for i, d in docs]


def extrair(texto):
    texto = re.sub(r"[*\s]*Resposta:?[*\s]*", "", texto)  # "**Resposta:** B" -> "B"
    m = re.match(r"\W*([ABCD])\b", texto) or re.search(r"\b([ABCD])\b", texto)
    return m.group(1) if m else None


def perguntar(mensagens):
    corpo = json.dumps({"model": "qwen", "messages": mensagens, "temperature": 0, "max_tokens": 4}).encode()
    for tentativa in range(3):
        try:
            req = urllib.request.Request(URL, data=corpo, headers={"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=1800))
            return (r["choices"][0]["message"]["content"] or ""), r["usage"]["completion_tokens"]
        except Exception:
            if tentativa == 2: raise
            time.sleep(5)


def um(item):
    texto, ntok = perguntar(item["mensagens"])
    letra = extrair(texto)
    return {"id": item["id"], "gold": item["gold"], "resposta": texto, "letra": letra, "acertou": int(letra == item["gold"]), "tokens": ntok}


def avaliar(bench, limite, trabalhadores=8):
    """Devolve (lista de resultados por questao, segundos)."""
    itens = itens_mmlu(limite) if bench == "mmlu_letra" else itens_oab(limite)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(trabalhadores) as ex:
        res = list(ex.map(um, itens))
    return res, time.perf_counter() - t0
