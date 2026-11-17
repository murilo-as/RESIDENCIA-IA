#!/bin/bash
# 4.2 Ruido dos benchmarks de codigo e dos outros: comparacao PAREADA f16 x q4_k_m (mesmas questoes) com pareado.py, para todos os modelos de amostras/. Nao usa GPU; so le amostras/. Saida: logs/ruido_pareado.md
# Ideia: o erro padrao de cada nota (3,2 a 3,7 pts no HumanEval+) mistura a dificuldade das questoes; o da diferenca pareada so conta as questoes em que os dois niveis discordam.
# ruido_pareado.py faz a tabela por modelo e prova, o resumo por prova e o diagnostico do MBPP+ do Qwen2.5-3B-Instruct (so diagnostica; nao altera resultados).
BLOCO=p4_2_ruido; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
marco 4
$PY ruido_pareado.py 2>&1 | tee -a $LOG
exit 0
