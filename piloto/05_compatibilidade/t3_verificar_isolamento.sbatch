#!/bin/bash
#SBATCH --job-name=piloto-t3iso
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:15:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/tmp_codigo
#SBATCH -o /beegfs/home/%u/work/tmp_codigo/isolamento-%j.out
#SBATCH -e /beegfs/home/%u/work/tmp_codigo/isolamento-%j.err
# Descricao: T3 parte 3 - verifica, SEM executar codigo gerado, o que o conteiner descartavel enxerga com --no-container-mount-home e so ~/work/tmp_codigo montado.

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh --no-container-mount-home \
     --container-mounts=/beegfs/home/user_muriloalves/work/tmp_codigo:/work \
     --container-workdir=/work \
     bash -c '
echo "##### ls -la da home"; ls -la /beegfs/home/user_muriloalves 2>&1 | head -20
echo "##### .triton visivel?"; ls -d /beegfs/home/user_muriloalves/.triton 2>&1
echo "##### outras areas do beegfs"; find /beegfs -maxdepth 3 2>&1 | head -20
echo "##### mounts relacionados"; grep -E "beegfs|/work" /proc/mounts | head
echo "##### /work"; ls /work
'
