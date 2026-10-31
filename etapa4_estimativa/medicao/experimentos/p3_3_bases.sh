#!/bin/bash
# 3.3 Bases e variantes, so f16 e so log-prob (mmlu, medqa, oab, pubmedqa). Um por vez; cada medicao tem no maximo 2 h (passou, pula e segue; o que ja saiu fica no CSV). Apaga o modelo ao terminar.
BLOCO=p3_3_bases; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen2.5-3B Qwen2.5-7B Qwen3-1.7B-Base Qwen3.5-2B-Base Qwen3.5-4B-Base Qwen3-8B-Base Qwen3.5-9B-Base Qwen2.5-14B Qwen3-30B-A3B-Base Qwen3.6-35B-A3B; do
  baixar Qwen/$M || { echo "$M: download falhou, pulado" | tee -a $LOG; continue; }
  med 2h --modelo $M --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa
  limpar $M --exigir mmlu medqa oab pubmedqa --niveis f16
done
exit 0
