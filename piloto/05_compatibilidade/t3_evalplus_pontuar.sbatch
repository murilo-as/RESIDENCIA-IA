#!/bin/bash
#SBATCH --job-name=piloto-t3score
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/tmp_codigo
#SBATCH -o /beegfs/home/%u/work/tmp_codigo/pontuar-%j.out
#SBATCH -e /beegfs/home/%u/work/tmp_codigo/pontuar-%j.err
# Descricao: T3 parte 3 - pontua com o evalplus as solucoes de HumanEval+ e MBPP+ DENTRO de um conteiner descartavel que so ve ~/work/tmp_codigo (sem a home, sem nome fixo, sem HF_ALLOW_CODE_EVAL); completa com solucao vazia os problemas nao gerados e calcula o pass@1 so dos gerados.

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh --no-container-mount-home \
     --container-mounts=/beegfs/home/user_muriloalves/work/tmp_codigo:/work \
     --container-workdir=/work \
     bash -c '
export HOME=/work XDG_CACHE_HOME=/work/cache PYTHONPATH=/work/pkgs
echo "##### o que o conteiner ve da home"
find /beegfs/home/user_muriloalves -maxdepth 3 2>&1 | head -20
echo "##### completar amostras"
python3 /work/pontuar_amostras.py completar
for d in humaneval mbpp; do
  echo "##### evalplus $d (todos os problemas; o pass@1 impresso aqui e diluido)"
  time python3 -m evalplus.evaluate --dataset $d --samples /work/samples/${d}_completo.jsonl 2>&1 | tail -12
done
echo "##### pass@1 so dos gerados"
python3 /work/pontuar_amostras.py resumir
'
