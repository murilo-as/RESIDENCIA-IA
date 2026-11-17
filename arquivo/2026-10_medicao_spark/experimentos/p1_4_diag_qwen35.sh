#!/bin/bash
# 1.4 Diagnostico do MMLU do Qwen3.5-9B (q4_k_m > f16): mesma amostra de 1425 questoes. (a) log-prob fp16 (reaproveita a linha ja medida), (b) log-prob bf16, (c) mmlu_letra f16, (d) mmlu_letra q4_k_m.
# Controle no Qwen3-8B: (a) e (c). Tudo em kv.csv com kv=16.
BLOCO=p1_4_diag; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
med 3h --modelo Qwen3.5-9B --niveis f16 --kv 16 --saida kv.csv --reusar-de resultados.csv --benchmarks mmlu_logprob_fp16 mmlu_logprob_bf16 mmlu_letra
med 2h --modelo Qwen3.5-9B --niveis q4_k_m --kv 16 --saida kv.csv --reusar-de resultados.csv --benchmarks mmlu_logprob_fp16 mmlu_letra
med 2h --modelo Qwen3-8B --niveis f16 --kv 16 --saida kv.csv --reusar-de resultados.csv --benchmarks mmlu_logprob_fp16 mmlu_letra
exit 0
