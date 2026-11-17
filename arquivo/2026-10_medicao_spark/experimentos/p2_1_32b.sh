#!/bin/bash
# 2.1 Qwen2.5-32B-Instruct sozinho no no (o log-prob expande para fp16, ~61 GiB; batch 2). Falta: oab e pubmedqa em f16; mmlu, medqa, oab, pubmedqa e gsm8k em q8_0 e q4_k_m.
# Os GGUF q8_0 e q4_k_m sao gerados do f16 pelo medir.py. Nao entra em outro bloco: apaga tudo no fim.
BLOCO=p2_1_32b; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
marco 2
M=Qwen2.5-32B-Instruct
med 4h --modelo $M --niveis f16 --batch-hf 2 --benchmarks oab pubmedqa
med 7h --modelo $M --niveis q8_0 --batch-hf 2 --benchmarks mmlu medqa oab pubmedqa gsm8k
med 6h --modelo $M --niveis q4_k_m --batch-hf 2 --benchmarks mmlu medqa oab pubmedqa gsm8k
limpar $M --exigir mmlu medqa oab pubmedqa gsm8k
exit 0
