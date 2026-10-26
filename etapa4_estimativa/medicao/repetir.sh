#!/bin/bash
# Roda DENTRO do container. Repete o que ficou faltando na fila: medir.py e retomavel e pula o que ja esta no CSV,
# entao basta chamar de novo para todos os modelos (so paga o TaskManager se houver trabalho pendente).
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
cd $D; mkdir -p logs
rodar() {  # modelo, benchmarks e flags...
  local m=$1; shift
  echo "$(date -u +%FT%TZ) inicio $m" | tee -a logs/repetir.txt
  timeout --kill-after=120 3h $PY medir.py --modelo $m "$@" > logs/repetir_$m.log 2>&1
  echo "$(date -u +%FT%TZ) fim $m rc=$?" | tee -a logs/repetir.txt
  pkill -f "llama-server -m" 2>/dev/null
}
A="--benchmarks medqa pubmedqa humaneval mbpp wmt24 math500 --respeitar-etapa1"
for m in Qwen2.5-7B-Instruct Qwen2.5-3B-Instruct Qwen2.5-14B-Instruct; do rodar $m $A; done
B="--benchmarks mmlu medqa gsm8k --sem-raciocinio"
for m in Qwen3-1.7B Qwen3-8B Qwen3.5-2B Qwen3.5-4B Qwen3.5-9B; do rodar $m $B; done
exit 0
