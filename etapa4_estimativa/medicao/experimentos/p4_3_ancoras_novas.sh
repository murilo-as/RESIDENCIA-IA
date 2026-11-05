#!/bin/bash
# 4.3 Ancoras que faltam para cada grupo de arquitetura ter um irmao medido (9 provas x 3 niveis, raciocinio desligado). Do menor para o maior; apaga o modelo ao terminar.
# Codigo: gera aqui e pontua no job isolado seguinte (p4-pontuar).
BLOCO=p4_3_ancoras; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
marco 4
for M in Qwen2.5-0.5B-Instruct Qwen3-0.6B Qwen3.5-0.8B Qwen2.5-1.5B-Instruct Qwen3-4B Qwen3-14B; do
  baixar Qwen/$M || { echo "$M: download falhou, pulado" | tee -a $LOG; continue; }
  med 8h --modelo $M --sem-raciocinio --benchmarks mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp
  limpar $M --exigir mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp
done
exit 0
