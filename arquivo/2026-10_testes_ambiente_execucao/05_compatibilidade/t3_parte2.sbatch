#!/bin/bash
#SBATCH --job-name=piloto-t3p2
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=03:00:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err
# Descricao: T3 parte 2 - Qwen3.5-9B Q4_K_M com MMLU --limit 20 antes e depois de tentar instalar flash-linear-attention e causal-conv1d so por pip (somente wheels, sem compilar).

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache WORLD_SIZE=1 RANK=0 LOCAL_RANK=0 MASTER_ADDR=127.0.0.1 MASTER_PORT=29500
rod() { venv/bin/python 05_compatibilidade/t3_mmlu_custo.py $1 qwen3.5-9b-q4_k_m.gguf Qwen3.5-9B 20 2>&1 | tr "\r" "\n" | grep -vE "it/s\]|rank0\]|^Overwriting|^Using the latest|^Found the latest"; }
echo "##### A) Qwen3.5-9B --limit 20 SEM flash-linear-attention"
rod qwen35_semfla
echo "##### B) pip: plano (dry-run, so wheels)"
venv/bin/pip install --dry-run --only-binary=:all: flash-linear-attention 2>&1 | tail -8 | cut -c1-400
venv/bin/pip install --dry-run --only-binary=:all: flash-linear-attention 2>&1 | grep -i "would install" | grep -qiE "(^| )torch-[0-9]" && { echo "ABORTA: o plano instalaria/trocaria o torch"; exit 0; }
echo "##### C) pip install flash-linear-attention (so wheel)"
venv/bin/pip install --only-binary=:all: flash-linear-attention 2>&1 | tail -8 | cut -c1-400
echo "##### D) pip install causal-conv1d (so wheel)"
venv/bin/pip install --only-binary=:all: causal-conv1d 2>&1 | tail -15 | cut -c1-500
venv/bin/pip list 2>/dev/null | grep -iE "^(torch|transformers|flash.linear|fla|causal|triton|einops) "
echo "##### E) Qwen3.5-9B --limit 20 COM o que instalou"
rod qwen35_comfla
'
