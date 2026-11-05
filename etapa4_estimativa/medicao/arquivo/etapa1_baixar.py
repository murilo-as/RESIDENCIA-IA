"""Etapa 1: baixa para o hf_cache os datasets novos (PubMedQA qiaojin e WMT24++ en-pt_BR) e mostra colunas e tamanhos."""
from datasets import load_dataset

for path, nome in [("qiaojin/PubMedQA", "pqa_labeled"), ("google/wmt24pp", "en-pt_BR")]:
    d = load_dataset(path, nome)
    for s, ds in d.items():
        print(f"{path} {nome} split {s}: {ds.num_rows} linhas; colunas: {ds.column_names}")
        print("  exemplo:", {k: str(v)[:100] for k, v in ds[0].items()})
    if nome == "en-pt_BR": print("  segmentos com is_bad_source:", sum(bool(x) for x in d["train"]["is_bad_source"]))
