#!/bin/bash
# Descricao: Clona e compila o llama.cpp com CUDA (refaz build/ do zero) e confirma llama-cli, llama-quantize, llama-bench e a GPU.
#SBATCH --job-name=piloto-build
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -ec '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
[ -d llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp
cd llama.cpp
git log -1 --format="commit %h %ci"
rm -rf build
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native -DLLAMA_CURL=OFF
cmake --build build --config Release -j 8
ls -la build/bin/llama-cli build/bin/llama-quantize build/bin/llama-bench
build/bin/llama-cli --list-devices
'
