#!/bin/bash
# Libera disco depois do GPQA: apaga pesos e GGUF dos modelos do GPQA que nao entram em mais nenhum bloco (so se TODAS as medidas, GPQA incluido, estiverem registradas; limpar.py recusa se faltar algo). Qwen2.5-3B-Instruct fica para o P2-b.
BLOCO=p4_5_limpar; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen2.5-7B-Instruct Qwen2.5-14B-Instruct Qwen3-8B Qwen3.5-9B; do
  limpar $M --exigir mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp gpqa --niveis f16
done
exit 0
