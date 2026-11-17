#!/bin/bash
# 4.1 Qwen3.5: MMLU por geracao da letra (mmlu_letra), 3 niveis, KV f16, em kv.csv. Motivo: o log-prob (hf) deu 9B f16 68,7 < 4B 71,2 e q4 > f16; por letra o 9B deu 80,2 (f16) e 79,2 (q4_k_m).
# So mmlu_letra: MedQA e OAB do Qwen3.5 por log-prob estao monotonicos. NAO usar oab_letra nas familias Qwen3/3.5: 65% das respostas do Qwen3-8B vieram sem letra (limite de 4 tokens).
# Ja existem no kv.csv: 9B f16 e q4_k_m. Falta: 2B e 4B (3 niveis) e 9B q8_0. Retomavel (pula o que ja esta no CSV).
BLOCO=p4_1_letra; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
marco 4
for M in Qwen3.5-2B Qwen3.5-4B Qwen3.5-9B; do
  baixar Qwen/$M || { echo "$M: download falhou, pulado" | tee -a $LOG; continue; }
  med 3h --modelo $M --kv 16 --saida kv.csv --benchmarks mmlu_letra
done
exit 0
