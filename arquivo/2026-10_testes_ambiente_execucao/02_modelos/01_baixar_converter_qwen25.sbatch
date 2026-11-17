#!/bin/bash
# Descricao: Baixa o Qwen2.5-7B-Instruct, converte para GGUF F16 e gera Q8_0 e Q4_K_M; instala as dependencias de conversao.
#SBATCH --job-name=piloto-modelo
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -ec '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache
venv/bin/pip install transformers sentencepiece gguf protobuf
mkdir -p /beegfs/home/user_muriloalves/work/models
venv/bin/python -c "from huggingface_hub import snapshot_download as d; print(d(\"Qwen/Qwen2.5-7B-Instruct\", local_dir=\"/beegfs/home/user_muriloalves/work/models/Qwen2.5-7B-Instruct\"))"
venv/bin/python llama.cpp/convert_hf_to_gguf.py /beegfs/home/user_muriloalves/work/models/Qwen2.5-7B-Instruct --outtype f16 --outfile /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-f16.gguf
llama.cpp/build/bin/llama-quantize /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-f16.gguf /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-q8_0.gguf Q8_0
llama.cpp/build/bin/llama-quantize /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-f16.gguf /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-q4_k_m.gguf Q4_K_M
ls -la /beegfs/home/user_muriloalves/work/models/*.gguf
du -h /beegfs/home/user_muriloalves/work/models/*.gguf
'
