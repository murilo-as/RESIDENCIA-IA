#!/bin/bash
# Roda DENTRO do container (via slurm/rodar.sbatch). Passos em sequencia; um passo que falha nao impede o proximo, salvo as regras abaixo:
# a fumaca (3B, MMLU limit 2 + GSM8K 20, 3 niveis) precisa passar para os passos completos rodarem; 14B so roda se o modelo foi baixado.
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
MODELOS=/beegfs/home/user_muriloalves/work/models
cd $D; mkdir -p logs
estado() { echo "$(date -u +%FT%TZ) $*" | tee -a logs/estado.txt; }
passo() {  # nome limite comando...
  local nome=$1 limite=$2; shift 2
  estado "inicio $nome (limite $limite)"
  timeout --kill-after=120 $limite "$@" > logs/$nome.log 2>&1
  local rc=$?
  pkill -f "llama-server -m" 2>/dev/null; pkill -f "04_gsm8k/proxy.py" 2>/dev/null
  estado "fim $nome rc=$rc"
  return $rc
}
tem() { [ -f $MODELOS/$1/config.json ] && ls $MODELOS/$1/*.safetensors >/dev/null 2>&1; }
S3=Qwen2.5-3B-Instruct; S7=Qwen2.5-7B-Instruct; S14=Qwen2.5-14B-Instruct
$PY -m py_compile medir.py pareado.py resumo.py baixar_modelos.py || { estado "ERRO de sintaxe nos scripts: abortando"; exit 2; }
tem $S3 || estado "modelo ausente: $S3"
tem $S14 || estado "modelo ausente: $S14"

ok=0
if tem $S3; then passo fumaca 2h $PY medir.py --modelo $S3 --mmlu-limit 2 --gsm8k-limit 20 --dir $D/fumaca && ok=1; fi
if [ $ok = 1 ]; then
  passo 3b 4h $PY medir.py --modelo $S3
  passo 7b 8h $PY medir.py --modelo $S7
  if tem $S14; then
    passo 14b-mmlu 4h $PY medir.py --modelo $S14 --benchmarks mmlu
    passo 14b-gsm-q4 3h $PY medir.py --modelo $S14 --benchmarks gsm8k --niveis q4_k_m
    passo 14b-gsm-f16 6h $PY medir.py --modelo $S14 --benchmarks gsm8k --niveis f16
    passo 14b-gsm-q8 4h $PY medir.py --modelo $S14 --benchmarks gsm8k --niveis q8_0
  fi
else
  estado "fumaca nao passou (ou 3B ausente): passos completos pulados"
fi
passo resumo 20m $PY resumo.py
estado "campanha terminou"
