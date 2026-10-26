LETRAS = ["A", "B", "C", "D"]
GABARITOS_EXEMPLOS = ["B", "D", "A", "C", "B"]  # letras variadas nos 5 exemplos, para nao induzir a resposta


def _validas(ds):
    return [i for i in range(len(ds)) if not ds[i]["nullified"] and ds[i]["choices"]["label"] == LETRAS and ds[i]["answerKey"] in LETRAS]


def _exemplos(ds):
    """Indices dos 5 exemplos fixos: de tras para frente, o primeiro valido com cada gabarito da lista (sempre os mesmos)."""
    usados = []
    for g in GABARITOS_EXEMPLOS:
        for i in reversed(_validas(ds)):
            if i not in usados and ds[i]["answerKey"] == g:
                usados.append(i)
                break
    return usados


def process_docs(dataset):
    """Questoes validas, sem as 5 usadas como exemplos (para o exemplo nunca ser pergunta)."""
    fora = set(_exemplos(dataset))
    return dataset.select([i for i in _validas(dataset) if i not in fora])


def list_fewshot_samples():
    from datasets import load_dataset
    ds = load_dataset("eduagarcia/oab_exams", split="train")
    return [dict(ds[i]) for i in _exemplos(ds)]


def doc_to_text(doc):
    alternativas = "\n".join(f"{l}. {t}" for l, t in zip(doc["choices"]["label"], doc["choices"]["text"]))
    return f"Pergunta: {doc['question']}\n{alternativas}\nResposta:"


def doc_to_target(doc):
    return LETRAS.index(doc["answerKey"])
