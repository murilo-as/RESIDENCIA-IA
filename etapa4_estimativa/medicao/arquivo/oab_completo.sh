#!/bin/bash
# Roda DENTRO do container. OAB completo (todas as questoes validas, 5-shot) nos 3 modelos e 3 niveis, so se o OAB passou na etapa 1 (--respeitar-etapa1 pula senao).
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
cd $D; mkdir -p logs
for M in Qwen2.5-7B-Instruct Qwen2.5-3B-Instruct Qwen2.5-14B-Instruct; do
  echo "$(date -u +%FT%TZ) inicio oab $M" | tee -a logs/oab_completo.txt
  timeout --kill-after=120 4h $PY medir.py --modelo $M --benchmarks oab --respeitar-etapa1 > logs/oab_completo_$M.log 2>&1
  echo "$(date -u +%FT%TZ) fim oab $M rc=$?" | tee -a logs/oab_completo.txt
  pkill -f "llama-server -m" 2>/dev/null
done
exit 0
