#!/bin/bash
# Descricao: Lista GPU, CUDA, Python, cmake, git, compilador e disco do no (dentro do container PyTorch). Nao instala nada.
#SBATCH --job-name=piloto-diag
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
#SBATCH --time=00:10:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c 'uname -m; echo "--- nvidia-smi"; nvidia-smi; echo "--- nvcc"; nvcc --version; echo "--- python3"; python3 --version; echo "--- cmake"; cmake --version; echo "--- git"; git --version; echo "--- make/gcc"; make --version | head -1; gcc --version | head -1; echo "--- disco"; df -h /beegfs/home/user_muriloalves; echo "--- mem"; free -g'
