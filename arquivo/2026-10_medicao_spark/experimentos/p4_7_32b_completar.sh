#!/bin/bash
# P2-c Completa o Qwen2.5-32B-Instruct: faltam math500, wmt24, humaneval e mbpp nos 3 niveis (o resto ja esta nos CSV). Sozinho no no; baixa de novo (foi apagado), gera os GGUF e apaga ao terminar.
# Codigo: gera aqui e pontua no job isolado seguinte.
BLOCO=p4_7_32b; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
M=Qwen2.5-32B-Instruct
usado=$(du -s --block-size=1G /beegfs/home/user_muriloalves/work/models | cut -f1)
if [ "$usado" -gt 250 ]; then echo "pasta de modelos com ${usado} GB: o 32B precisa de ~190 GB livres dentro do limite de 450; bloco cancelado" | tee -a $LOG | tee -a erros.log; exit 0; fi
baixar Qwen/$M || { echo "$M: download falhou, bloco cancelado" | tee -a $LOG; exit 0; }
med 9h --modelo $M --niveis f16 --batch-hf 2 --benchmarks math500 wmt24 humaneval mbpp
med 7h --modelo $M --niveis q8_0 --batch-hf 2 --benchmarks math500 wmt24 humaneval mbpp
med 6h --modelo $M --niveis q4_k_m --batch-hf 2 --benchmarks math500 wmt24 humaneval mbpp
limpar $M --exigir mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp
exit 0
