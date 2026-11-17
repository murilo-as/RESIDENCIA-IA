LETRAS = ["A", "B", "C", "D"]


def process_docs(dataset):
    """Mantem so questoes validas: nao anuladas, com 4 alternativas A-D e gabarito A-D."""
    return dataset.filter(lambda d: not d["nullified"] and d["choices"]["label"] == LETRAS and d["answerKey"] in LETRAS)


def doc_to_text(doc):
    alternativas = "\n".join(f"{l}. {t}" for l, t in zip(doc["choices"]["label"], doc["choices"]["text"]))
    return f"Pergunta: {doc['question']}\n{alternativas}\nResposta:"


def doc_to_target(doc):
    return LETRAS.index(doc["answerKey"])
