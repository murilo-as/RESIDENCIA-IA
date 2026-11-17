#!/bin/bash
#SBATCH --job-name=piloto-t3dados
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err
# Descricao: T3 parte 3 - baixa para o hf_cache MedQA, PubMedQA, MATH-500, OAB-Exams, HumanEval+ e MBPP+ (GPQA e WMT24++ ficam de fora) e mostra splits, colunas e os campos do OAB-Exams.

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache
venv/bin/python 05_compatibilidade/t3_baixar_datasets.py 2>&1 | tr "\r" "\n" | grep -vE "it/s\]|Generating|Downloading|^$"
'
