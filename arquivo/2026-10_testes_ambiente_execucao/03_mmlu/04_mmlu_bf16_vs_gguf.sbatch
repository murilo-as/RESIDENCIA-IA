#!/bin/bash
# Descricao: MMLU 5-shot (--limit 10 por assunto, seed 42) no bf16 original, GGUF F16 e GGUF Q4_K_M via transformers; resultados em resultados/.
#SBATCH --job-name=piloto-mmlu
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

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache
export WORLD_SIZE=1 RANK=0 LOCAL_RANK=0 MASTER_ADDR=127.0.0.1 MASTER_PORT=29500
mkdir -p resultados
rodar() {
  echo "##### $1"
  time timeout 3000 venv/bin/lm_eval --model hf --model_args "$2" --device cuda \
    --tasks mmlu --num_fewshot 5 --limit 10 --seed 42 --batch_size 1 \
    --output_path resultados/$1 2>&1 | tr "\r" "\n" | grep -v "it/s\]" | tail -20
}
rodar bf16 pretrained=/beegfs/home/user_muriloalves/work/models/Qwen2.5-7B-Instruct,dtype=bfloat16
rodar gguf-f16 pretrained=/beegfs/home/user_muriloalves/work/models,gguf_file=qwen2.5-7b-instruct-f16.gguf,tokenizer=/beegfs/home/user_muriloalves/work/models/Qwen2.5-7B-Instruct,dtype=float16
rodar gguf-q4km pretrained=/beegfs/home/user_muriloalves/work/models,gguf_file=qwen2.5-7b-instruct-q4_k_m.gguf,tokenizer=/beegfs/home/user_muriloalves/work/models/Qwen2.5-7B-Instruct,dtype=float32
'
