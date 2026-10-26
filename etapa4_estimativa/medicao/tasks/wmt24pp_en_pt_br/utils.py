def process_docs(dataset):
    """Mantem so os segmentos cuja fonte nao foi marcada como ruim."""
    return dataset.filter(lambda d: not d.get("is_bad_source", False))


def doc_to_text(doc):
    return f"Translate the following text from English into Brazilian Portuguese. Reply with the translation only.\n\n{doc['source']}"
