#!/bin/bash
#SBATCH --job-name=piloto-t3p1off
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
# Descricao: T3 parte 1, terceira rodada - MMLU --limit 20 do Qwen2.5-7B Q4_K_M com HF_DATASETS_OFFLINE=1, para comparar com a rodada normal (job 873).

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache WORLD_SIZE=1 RANK=0 LOCAL_RANK=0 MASTER_ADDR=127.0.0.1 MASTER_PORT=29500
export HF_DATASETS_OFFLINE=1
echo "##### qwen2.5-7b Q4_K_M, --limit 20, HF_DATASETS_OFFLINE=1"
venv/bin/python 05_compatibilidade/t3_mmlu_custo.py qwen25_offline qwen2.5-7b-instruct-q4_k_m.gguf Qwen2.5-7B-Instruct 20 2>&1 | tr "\r" "\n" | grep -vE "it/s\]|rank0\]|^Overwriting|^Using the latest|^Found the latest"
'
