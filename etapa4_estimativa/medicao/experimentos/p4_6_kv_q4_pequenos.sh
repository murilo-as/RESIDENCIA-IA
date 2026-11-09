#!/bin/bash
# P2-b KV q4_0 nos modelos pequenos (Qwen2.5-3B-Instruct e 1.5B-Instruct), pesos Q8_0: teste da regra de risco do KV (no 7B o KV q4_0 quebrou; no 14B e no Qwen3-8B ficou normal).
# kv=16 de gsm8k/math500 reaproveita resultados.csv; as provas de letra rodam nos dois KV. 'cortadas' = sem letra / sem resposta: separa falha de formato de perda de acerto. Se K e V em q4_0 nao subirem (rc 4), usa k4v8.
BLOCO=p4_6_kv_q4; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen2.5-3B-Instruct Qwen2.5-1.5B-Instruct; do
  baixar Qwen/$M || { echo "$M: download falhou, pulado" | tee -a $LOG; continue; }
  for KV in 16 4; do
    med 6h --modelo $M --niveis q8_0 --kv $KV --saida kv.csv --reusar-de resultados.csv --benchmarks gsm8k math500 mmlu_letra oab_letra
    if [ $? -eq 4 ] && [ $KV = 4 ]; then
      echo "$(date -u +%FT%TZ) $M: K e V em q4_0 falharam; tentando K q4_0 + V q8_0" | tee -a $LOG
      med 6h --modelo $M --niveis q8_0 --kv k4v8 --saida kv.csv --benchmarks gsm8k math500 mmlu_letra oab_letra
    fi
  done
  limpar $M --exigir mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp
done
exit 0
