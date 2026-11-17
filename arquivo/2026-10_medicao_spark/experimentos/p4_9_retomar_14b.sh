#!/bin/bash
# Retoma o Qwen3-14B (q8_0 e q4_k_m) que parou em 06/11 por espaco (pasta de modelos acima de 450 GB; criou o arquivo PARAR).
# Libera antes Qwen3.5-2B e 4B (todas as medidas deles ja estao registradas; limpar.py confere), remove o PARAR e mede o que falta (retomavel).
BLOCO=p4_9_retomar_14b; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen3.5-2B Qwen3.5-4B; do
  limpar $M --exigir mmlu medqa gsm8k oab pubmedqa math500 wmt24 humaneval mbpp mmlu_letra
done
du -sh /beegfs/home/user_muriloalves/work/models | tee -a $LOG
usado=$(du -s --block-size=1G /beegfs/home/user_muriloalves/work/models | cut -f1)
if [ "$usado" -lt 400 ]; then rm -f PARAR; else echo "pasta de modelos com ${usado} GB: mantendo PARAR" | tee -a $LOG; exit 0; fi
med 14h --modelo Qwen3-14B --sem-raciocinio --niveis q8_0 q4_k_m --benchmarks mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp
limpar Qwen3-14B --exigir mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp
exit 0
