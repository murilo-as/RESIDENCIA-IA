#!/bin/bash
# Escreve resumo_prioridade_N.md (N = $1) e atualiza resumo.md.
BLOCO=resumo_p$1; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
$PY resumo_prioridade.py $1 2>&1 | tee -a $LOG
$PY resumo.py > /dev/null 2>&1
exit 0
