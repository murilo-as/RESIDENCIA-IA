#!/bin/bash
# 1.2 KV quantizado: pesos Q8_0, KV f16 (16), q8_0 (8) e q4_0 (4), nos 3 modelos. gsm8k e math500 com kv=16 reaproveitam resultados.csv (mesma configuracao) quando existem.
# Se o servidor nao subir com K e V em q4_0 (codigo de saida 4), repete com K q4_0 e V q8_0 (kv=k4v8) e registra.
BLOCO=p1_2_kv; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen2.5-7B-Instruct Qwen2.5-14B-Instruct Qwen3-8B; do
  for KV in 16 8 4; do
    med 8h --modelo $M --niveis q8_0 --kv $KV --saida kv.csv --reusar-de resultados.csv --benchmarks gsm8k math500 mmlu_letra oab_letra
    if [ $? -eq 4 ] && [ $KV = 4 ]; then
      echo "$(date -u +%FT%TZ) $M: K e V em q4_0 falharam; tentando K q4_0 + V q8_0" | tee -a $LOG
      med 8h --modelo $M --niveis q8_0 --kv k4v8 --saida kv.csv --benchmarks gsm8k math500 mmlu_letra oab_letra
    fi
  done
done
exit 0
