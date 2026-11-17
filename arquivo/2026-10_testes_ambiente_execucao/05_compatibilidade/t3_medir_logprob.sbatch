#!/bin/bash
#SBATCH --job-name=piloto-t3lp
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err
# Descricao: T3 parte 3 - mede 20 exemplos de MMLU (abstract_algebra), MedQA e OAB-Exams por log-prob no Qwen2.5-7B Q4_K_M: segundos por exemplo e tokens de contexto.

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache HF_DATASETS_OFFLINE=1 WORLD_SIZE=1 RANK=0 LOCAL_RANK=0 MASTER_ADDR=127.0.0.1 MASTER_PORT=29500
venv/bin/python 05_compatibilidade/t3_medir_logprob.py mmlu_abstract_algebra medqa_4options oab_exams 2>&1 | tr "\r" "\n" | grep -vE "it/s\]|rank0\]|^Overwriting|^Using the latest|^Found the latest"
'
