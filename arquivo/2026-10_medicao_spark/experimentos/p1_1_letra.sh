#!/bin/bash
# 1.1 Valida a geracao de letra (mmlu_letra, oab_letra) no Qwen2.5-7B-Instruct f16 contra o log-prob. Grava em kv.csv com kv=16.
BLOCO=p1_1_letra; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
marco 1
med 3h --modelo Qwen2.5-7B-Instruct --niveis f16 --kv 16 --saida kv.csv --benchmarks mmlu_letra oab_letra
$PY validar_letra.py 2>&1 | tee -a $LOG
exit 0
