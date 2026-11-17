#!/bin/bash
# 1.5 Completa o que o timeout de 6 h do 1.3 deixou de fora: Qwen3.5-9B q4_k_m math500 (retomavel: pula o que ja esta no CSV).
BLOCO=p1_5_completar; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
med 4h --modelo Qwen3.5-9B --sem-raciocinio --niveis q4_k_m --benchmarks math500
exit 0
