#!/bin/bash
# Descricao: Mesma pergunta nos Q4_K_M do Qwen3 e Qwen3.5, e llama-bench (pp512, tg128) do Qwen2.5-7B em F16, Q8_0 e Q4_K_M.
#SBATCH --job-name=piloto-teste2
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --gres=gpu:1
#SBATCH --time=00:45:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
for l in qwen3-8b qwen3.5-9b; do
  echo "##### $l"
  [ -f /beegfs/home/user_muriloalves/work/models/$l-q4_k_m.gguf ] && llama.cpp/build/bin/llama-cli -m /beegfs/home/user_muriloalves/work/models/$l-q4_k_m.gguf -ngl 99 -n 128 --single-turn -p "Qual é a capital do Brasil? Responda em uma frase." || echo "FALHOU ou ausente: $l"
done
echo "##### llama-bench"
llama.cpp/build/bin/llama-bench -ngl 99 -p 512 -n 128 \
  -m /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-f16.gguf -m /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-q8_0.gguf -m /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-q4_k_m.gguf
'
