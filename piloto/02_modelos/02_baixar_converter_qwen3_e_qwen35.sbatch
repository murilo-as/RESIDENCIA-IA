#!/bin/bash
# Descricao: Baixa Qwen3-8B e Qwen3.5-9B, converte cada um para GGUF F16 e gera Q4_K_M. Se um falhar, segue para o outro.
#SBATCH --job-name=piloto-conv
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
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache
for m in Qwen3-8B Qwen3.5-9B; do
  l=$(echo $m | tr A-Z a-z)
  echo "##### $m"
  venv/bin/python -c "from huggingface_hub import snapshot_download as d; print(d(\"Qwen/$m\", local_dir=\"/beegfs/home/user_muriloalves/work/models/$m\"))" \
  && venv/bin/python llama.cpp/convert_hf_to_gguf.py /beegfs/home/user_muriloalves/work/models/$m --outtype f16 --outfile /beegfs/home/user_muriloalves/work/models/$l-f16.gguf \
  && llama.cpp/build/bin/llama-quantize /beegfs/home/user_muriloalves/work/models/$l-f16.gguf /beegfs/home/user_muriloalves/work/models/$l-q4_k_m.gguf Q4_K_M \
  && echo "OK $m" || echo "FALHOU $m"
done
ls -la /beegfs/home/user_muriloalves/work/models/*.gguf
'
