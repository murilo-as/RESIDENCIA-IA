#!/bin/bash
# roda os casos em sequência; se um falhar, segue para o próximo
cd "$(dirname "$0")"
mkdir -p logs_casos
CASOS="c13 c16 c12 c15 c3 c14"
for c in $CASOS; do
  echo "=== $c: $(date) ===" | tee -a logs_casos/resumo.txt
  python etapa7_executar_verificar/verificar.py $c --dry-run > logs_casos/${c}_dryrun.log 2>&1
  python etapa7_executar_verificar/verificar.py $c > logs_casos/$c.log 2>&1
  echo "$c terminou com código $? em $(date)" | tee -a logs_casos/resumo.txt
done
