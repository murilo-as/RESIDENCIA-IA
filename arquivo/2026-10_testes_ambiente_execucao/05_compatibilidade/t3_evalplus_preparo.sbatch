#!/bin/bash
#SBATCH --job-name=piloto-t3evp
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/logs
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err
# Descricao: T3 parte 3 - instala o evalplus (pip --target) e busca os dados do HumanEval+ e MBPP+ na pasta temporaria ~/work/tmp_codigo. Nao roda codigo gerado.

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-mounts=/beegfs/home/user_muriloalves/work/tmp_codigo:/work \
     bash -c '
export HOME=/work XDG_CACHE_HOME=/work/cache
python3 -m pip install --target /work/pkgs evalplus 2>&1 | tail -6 | cut -c1-300
PYTHONPATH=/work/pkgs python3 -c "
import evalplus; print(\"evalplus\", getattr(evalplus, \"__version__\", \"?\"))
from evalplus.data import get_human_eval_plus, get_mbpp_plus
print(\"HumanEval+:\", len(get_human_eval_plus()), \"problemas\")
print(\"MBPP+:\", len(get_mbpp_plus()), \"problemas\")
"
find /work/cache -type f | head
'
