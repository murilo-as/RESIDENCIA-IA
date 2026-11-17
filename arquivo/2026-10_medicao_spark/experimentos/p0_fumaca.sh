#!/bin/bash
# 0. Teste rapido dos caminhos novos do medir.py antes da campanha (Qwen3-1.7B, poucas questoes, tudo em fumaca/p2/): sintaxe, KV q8_0 + letra + memoria, raciocinio ligado,
# reaproveitamento de linhas, log-prob bf16, teste de 5 exemplos (math500 com prompt de sistema e codigo), resumo_prioridade e limpar (que nao pode apagar nada aqui).
BLOCO=p0_fumaca; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for f in *.py experimentos/*.py; do $PY -m py_compile $f && echo "sintaxe ok $f" || echo "SINTAXE FALHOU $f"; done 2>&1 | tee -a $LOG
for f in experimentos/*.sh; do bash -n $f && echo "sintaxe ok $f" || echo "SINTAXE FALHOU $f"; done 2>&1 | tee -a $LOG
F=fumaca/p2; mkdir -p $F; cp resultados.csv $F/resultados.csv
med 40m --dir $F --modelo Qwen3-1.7B --niveis q4_k_m --kv 8 --saida kv.csv --benchmarks mmlu_letra oab_letra --limites mmlu_letra=1 oab_letra=40
med 40m --dir $F --modelo Qwen3-1.7B --niveis q4_k_m --raciocinio-ligado --saida raciocinio.csv --benchmarks gsm8k math500 --limites gsm8k=6 math500=6
med 40m --dir $F --modelo Qwen3-1.7B --niveis f16 --kv 16 --saida kv.csv --reusar-de resultados.csv --benchmarks mmlu_logprob_fp16 mmlu_logprob_bf16 gsm8k --limites mmlu_logprob_bf16=1
med 40m --dir $F --modelo Qwen3-1.7B --niveis q4_k_m --benchmarks math500 humaneval --limites math500=5 humaneval=5 --sistema 'Please reason step by step, and put your final answer within \boxed{}.'
$PY resumo_prioridade.py 0 2>&1 | tee -a $LOG; rm -f resumo_prioridade_0.md
$PY limpar.py Qwen3-1.7B --exigir oab mmlu 2>&1 | tee -a $LOG
for f in $F/*.csv; do echo "== $f"; cat $f; done 2>&1 | tee -a $LOG
cat $F/erros.log 2>/dev/null | cut -c1-300 | tail -40 | tee -a $LOG
exit 0
