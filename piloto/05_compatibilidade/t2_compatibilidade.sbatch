#!/bin/bash
#SBATCH --job-name=piloto-t2
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:30:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err
# Descricao: T2 - tenta carregar os GGUF Q4_K_M do Qwen3-8B e Qwen3.5-9B com transformers (float16) e roda MMLU 5-shot --limit 2; cada modelo em um processo, se um falhar segue para o outro.

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache WORLD_SIZE=1 RANK=0 LOCAL_RANK=0 MASTER_ADDR=127.0.0.1 MASTER_PORT=29500
for a in "qwen3-8b qwen3-8b-q4_k_m.gguf Qwen3-8B" "qwen3.5-9b qwen3.5-9b-q4_k_m.gguf Qwen3.5-9B"; do
  venv/bin/python 05_compatibilidade/t2_qwen3_qwen35_gguf.py $a 2>&1 | tr "\r" "\n" | grep -vE "it/s\]|rank0\]|^Overwriting default"
done
'
