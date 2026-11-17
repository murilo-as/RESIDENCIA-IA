#!/bin/bash
# Ajuste de 09/11: mmlu_letra do Qwen3.5-0.8B nos 3 niveis (kv=16, kv.csv, raciocinio desligado). NAO roda oab_letra em Qwen3/Qwen3.5 (respostas sem letra). O modelo foi apagado depois do P1: baixa de novo e apaga ao fim.
BLOCO=p4_10_letra_08b; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
M=Qwen3.5-0.8B
baixar Qwen/$M || { echo "$M: download falhou, bloco cancelado" | tee -a $LOG; exit 0; }
med 2h --modelo $M --niveis f16 q8_0 q4_k_m --kv 16 --saida kv.csv --benchmarks mmlu_letra
limpar $M --exigir mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp mmlu_letra
exit 0
