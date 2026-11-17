#!/bin/bash
# Libera disco depois do GPQA: apaga pesos e GGUF dos modelos do GPQA que nao entram em mais nenhum bloco, SO se o GPQA f16 do modelo estiver no resultados.csv e todas as outras medidas (3 niveis) tambem
# (limpar.py recusa se faltar algo). Se o GPQA nao rodou (acesso ao dataset), nada e apagado e os blocos grandes seguintes se auto-cancelam por falta de espaco. Qwen2.5-3B-Instruct fica para o P2-b.
BLOCO=p4_5_limpar; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen2.5-7B-Instruct Qwen2.5-14B-Instruct Qwen3-8B Qwen3.5-9B; do
  if grep -q "^$M,f16,gpqa," resultados.csv; then
    limpar $M --exigir mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp
  else
    echo "$M: sem GPQA f16 no resultados.csv; nao apagado" | tee -a $LOG
  fi
done
du -sh /beegfs/home/user_muriloalves/work/models | tee -a $LOG
exit 0
