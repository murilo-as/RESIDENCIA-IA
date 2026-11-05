#!/bin/bash
# 4.2 Ruido dos benchmarks de codigo e dos outros: comparacao PAREADA f16 x q4_k_m (mesmas questoes) com pareado.py. Nao usa GPU; so le amostras/. Saida: logs/ruido_pareado.md
# Ideia: o erro padrao de cada nota (3,2 a 3,7 pts no HumanEval+) mistura a dificuldade das questoes; o da diferenca pareada so conta as questoes em que os dois niveis discordam.
BLOCO=p4_2_ruido; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
marco 4
out=logs/ruido_pareado.md; echo "# Comparacao pareada f16 x q4_k_m ($(date -u +%F))" > $out
for M in $(ls amostras); do
  for B in mmlu medqa oab pubmedqa gsm8k math500 humaneval_plus mbpp_plus; do
    echo "## $M $B" >> $out; $PY pareado.py $M f16 q4_k_m $B >> $out 2>&1
  done
done
echo "pareado: $(grep -c '^## ' $out) comparacoes em $out" | tee -a $LOG
exit 0
