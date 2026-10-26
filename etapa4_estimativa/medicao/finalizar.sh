#!/bin/bash
# Roda DENTRO do container (via slurm/rodar.sbatch): grava no CSV a pontuacao de codigo e escreve resumo.md.
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
cd $D
$PY medir.py --ingerir-codigo
$PY resumo.py
