#!/bin/bash
cd "$(dirname "$0")"
for c in c13 c12; do
  echo "=== $c (batch-hf 1): $(date) ===" | tee -a logs_casos/resumo.txt
  python etapa7_executar_verificar/verificar.py $c --batch-hf 1 > logs_casos/${c}_b1.log 2>&1
  echo "$c terminou com código $? em $(date)" | tee -a logs_casos/resumo.txt
done
