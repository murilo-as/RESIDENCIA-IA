#!/bin/bash
# Descricao: Cria o venv (com os pacotes do container) e instala o lm-evaluation-harness. So instala, nao roda benchmark.
#SBATCH --job-name=piloto-venv
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -ec '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
python3 -m venv --system-site-packages venv
venv/bin/pip install lm-eval
venv/bin/pip list 2>/dev/null | grep -iE "^(lm.eval|torch|transformers|datasets|huggingface.hub) "
venv/bin/lm_eval --help | head -3
'
