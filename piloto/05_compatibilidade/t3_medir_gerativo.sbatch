#!/bin/bash
#SBATCH --job-name=piloto-t3gen
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --gres=gpu:1
#SBATCH --time=01:30:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err
# Descricao: T3 parte 3 - mede 20 exemplos gerativos (GSM8K, MATH-500) pelo llama-server e gera as solucoes de HumanEval+ e MBPP+ para o evalplus; este job tem a home montada e NAO executa codigo.

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/05_compatibilidade/t3_medir_gerativo.sh
