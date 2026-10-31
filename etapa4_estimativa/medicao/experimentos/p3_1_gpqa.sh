#!/bin/bash
# 3.1 GPQA Diamond em f16 (zero-shot, log-prob) em 5 modelos. So roda se o HF_TOKEN valer DENTRO do job e os termos do dataset tiverem sido aceitos (teste com 1 exemplo).
# O token vem do .env sem ser impresso nem gravado em log.
BLOCO=p3_1_gpqa; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
marco 3
ENV=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/.env
if [ -z "$HF_TOKEN" ] && [ -f "$ENV" ]; then
  HF_TOKEN=$(grep -E '^(export )?HF_TOKEN=' "$ENV" | head -1 | sed -E 's/^(export )?HF_TOKEN=//; s/^["'"'"']//; s/["'"'"']$//'); export HF_TOKEN
fi
export HF_DATASETS_OFFLINE=0 HF_HUB_OFFLINE=0
if [ -z "$HF_TOKEN" ]; then echo "HF_TOKEN nao esta visivel dentro do job (variavel vazia e sem .env legivel)" | tee logs/p3_1_gpqa_acesso.txt | tee -a $LOG; exit 0; fi
$PY experimentos/gpqa_acesso.py 2>&1 | tee logs/p3_1_gpqa_acesso.txt | tee -a $LOG
if grep -q '^sucesso' logs/p3_1_gpqa_acesso.txt; then
  for M in Qwen2.5-3B-Instruct Qwen2.5-7B-Instruct Qwen2.5-14B-Instruct Qwen3-8B Qwen3.5-9B; do
    med 3h --modelo $M --niveis f16 --benchmarks gpqa
  done
fi
exit 0
