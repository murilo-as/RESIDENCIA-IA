ALTERNATIVAS = ["yes", "no", "maybe"]


def doc_to_text(doc):
    contextos = "\n".join(doc["context"]["contexts"])
    return f"Abstract: {contextos}\nQuestion: {doc['question']}\nAnswer:"


def doc_to_target(doc):
    return ALTERNATIVAS.index(doc["final_decision"])
