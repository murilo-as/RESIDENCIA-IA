#!/bin/bash
# Descricao: Pergunta curta em portugues ao Qwen2.5-7B Q4_K_M com llama-cli, para ver a resposta e os tokens/s.
#SBATCH --job-name=piloto-teste
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --gres=gpu:1
#SBATCH --time=00:15:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
llama.cpp/build/bin/llama-cli --help 2>&1 | grep -iE "single-turn|conversation" | head
llama.cpp/build/bin/llama-cli -m /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-q4_k_m.gguf -ngl 99 -n 128 --single-turn -p "Qual é a capital do Brasil? Responda em uma frase."
'
