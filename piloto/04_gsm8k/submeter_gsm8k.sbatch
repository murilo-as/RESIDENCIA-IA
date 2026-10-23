#!/bin/bash
# Descricao: Submete as 3 rodadas de GSM8K: Qwen2.5-7B Q4_K_M, Qwen3-8B Q4_K_M com raciocinio ligado e desligado.
#SBATCH --job-name=piloto-gsm8k
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
04_gsm8k/rodar_rodada.sh qwen25-q4km qwen2.5-7b-instruct-q4_k_m.gguf on
04_gsm8k/rodar_rodada.sh qwen3-think qwen3-8b-q4_k_m.gguf on
04_gsm8k/rodar_rodada.sh qwen3-nothink qwen3-8b-q4_k_m.gguf off
'
