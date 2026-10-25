"""T3 parte 3: baixa para o hf_cache os datasets abertos do inventario e imprime splits, colunas e uma linha. Cada dataset em try/except."""
import collections, traceback
from datasets import load_dataset

LISTA = [("GBaker/MedQA-USMLE-4-options-hf", None), ("bigbio/pubmed_qa", "pubmed_qa_labeled_fold0_source"),
         ("HuggingFaceH4/MATH-500", None), ("eduagarcia/oab_exams", None),
         ("evalplus/humanevalplus", None), ("evalplus/mbppplus", None)]
for path, nome in LISTA:
    print(f"##### {path} {nome or ''}")
    try:
        d = load_dataset(path, nome) if nome else load_dataset(path)
        for s, ds in d.items(): print(f"  split {s}: {ds.num_rows} linhas; colunas: {ds.column_names}")
        s0 = "test" if "test" in d else list(d)[0]
        print("  exemplo:", {k: (str(v)[:120]) for k, v in d[s0][0].items()})
        if path == "eduagarcia/oab_exams":
            ds = d["train"]
            for col in ("exam_id", "exam_year", "question_type", "nullified"):
                c = collections.Counter(ds[col])
                print(f"  {col}: {len(c)} valores; mais comuns: {c.most_common(12)}")
            print("  answerKey:", collections.Counter(ds["answerKey"]).most_common())
            print("  n de alternativas:", collections.Counter(len(x["label"]) for x in ds["choices"]).most_common())
    except Exception:
        print("  FALHOU:\n" + traceback.format_exc())
