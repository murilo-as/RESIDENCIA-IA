#!/bin/bash
# 1.3 Provas que faltam nas ancoras (3 niveis): oab, pubmedqa (log-prob), math500, wmt24, humaneval_plus, mbpp_plus (gerar; a pontuacao vem no job isolado seguinte).
# Os tres modelos menores nao entram em mais nenhum bloco: depois de todas as medidas, apaga pesos e GGUFs para liberar disco.
BLOCO=p1_3_ancoras; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen3-1.7B Qwen3.5-2B Qwen3.5-4B Qwen3-8B Qwen3.5-9B; do
  med 6h --modelo $M --sem-raciocinio --benchmarks oab pubmedqa math500 wmt24 humaneval mbpp
done
for M in Qwen3-1.7B Qwen3.5-2B Qwen3.5-4B; do
  limpar $M --exigir mmlu medqa gsm8k oab pubmedqa math500 wmt24 humaneval mbpp
done
exit 0
