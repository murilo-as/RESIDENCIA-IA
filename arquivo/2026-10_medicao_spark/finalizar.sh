#!/bin/bash
# Roda DENTRO do container (via slurm/rodar.sbatch): grava no CSV a pontuacao de codigo e escreve resumo.md.
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=$(for v in /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/venv /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv; do [ -x $v/bin/python ] && echo $v/bin/python && break; done)  # venv na raiz se existir; neste cluster fica em piloto/venv
cd $D
$PY medir.py --ingerir-codigo
$PY resumo.py
