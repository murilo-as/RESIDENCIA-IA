#!/bin/bash
# 2.3 Raciocinio ligado: Qwen3-8B e Qwen3.5-9B em q4_k_m, gsm8k e math500, ate 4096 tokens por resposta (contexto 65536 = 8 slots de 8192). Grava em raciocinio.csv.
BLOCO=p2_3_raciocinio; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen3-8B Qwen3.5-9B; do
  med 12h --modelo $M --niveis q4_k_m --raciocinio-ligado --saida raciocinio.csv --benchmarks gsm8k math500
done
exit 0
