#!/bin/bash
# Descricao: Teste de funcionamento (mmlu abstract_algebra, --limit 3) de --model hf no bf16 original e no Q4_K_M via gguf_file. Funcionou.
#SBATCH --job-name=piloto-probe5
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

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache
export WORLD_SIZE=1 RANK=0 LOCAL_RANK=0 MASTER_ADDR=127.0.0.1 MASTER_PORT=29500
venv/bin/pip list 2>/dev/null | grep -iE "^(torch|accelerate|transformers) "
echo "##### hf bf16 original"
time timeout 1500 venv/bin/lm_eval --model hf \
  --model_args pretrained=/beegfs/home/user_muriloalves/work/models/Qwen2.5-7B-Instruct,dtype=bfloat16 \
  --device cuda --tasks mmlu_abstract_algebra --num_fewshot 5 --limit 3 --batch_size 1 2>&1 | tr "\r" "\n" | grep -v "it/s\]" | tail -25
echo "##### hf gguf Q4_K_M"
time timeout 1500 venv/bin/lm_eval --model hf \
  --model_args pretrained=/beegfs/home/user_muriloalves/work/models,gguf_file=qwen2.5-7b-instruct-q4_k_m.gguf,tokenizer=/beegfs/home/user_muriloalves/work/models/Qwen2.5-7B-Instruct,dtype=bfloat16 \
  --device cuda --tasks mmlu_abstract_algebra --num_fewshot 5 --limit 3 --batch_size 1 2>&1 | tr "\r" "\n" | grep -v "it/s\]" | tail -25
'
