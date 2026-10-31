#!/bin/bash
# Funcoes comuns dos blocos da campanha. Roda DENTRO do container (slurm/rodar.sbatch). Uso nos blocos:  BLOCO=p1_1_letra; source experimentos/comum.sh
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
cd $D; mkdir -p logs/blocos
LOG=logs/blocos/$BLOCO.txt   # marcas de inicio/fim; a saida completa dos programas vai para logs/blocos/$BLOCO.log

marco() { [ -f logs/blocos/prioridade_$1.inicio ] || date -u +%FT%TZ > logs/blocos/prioridade_$1.inicio; }

med() {  # tempo-maximo e argumentos do medir.py (retomavel: pula o que ja esta nos CSV)
  local t=$1; shift
  echo "$(date -u +%FT%TZ) inicio medir.py $*" | tee -a $LOG
  timeout --kill-after=120 $t $PY medir.py "$@" >> logs/blocos/$BLOCO.log 2>&1
  local rc=$?
  echo "$(date -u +%FT%TZ) fim rc=$rc" | tee -a $LOG
  pkill -f "llama-server -m" 2>/dev/null; sleep 5
  return $rc
}

baixar() {  # repositorios do Hugging Face (ex.: Qwen/Qwen2.5-Coder-3B-Instruct); falha nao derruba o bloco
  echo "$(date -u +%FT%TZ) baixar $*" | tee -a $LOG
  timeout --kill-after=60 1h $PY baixar_modelos.py "$@" >> logs/blocos/$BLOCO.log 2>&1
  local rc=$?
  echo "$(date -u +%FT%TZ) baixar rc=$rc" | tee -a $LOG
  return $rc
}

limpar() { $PY limpar.py "$@" 2>&1 | tee -a $LOG; }  # ver limpar.py: so apaga se todas as medidas do modelo estiverem registradas
