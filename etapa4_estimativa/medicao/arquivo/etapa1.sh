#!/bin/bash
# Roda DENTRO do container (via slurm/rodar.sbatch). Etapa 1: testes de aceite dos benchmarks novos; o veredito sai em etapa1.json.
# Uso: etapa1.sh <log do t3_verificar_isolamento.sbatch>
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
TMP=/beegfs/home/user_muriloalves/work/tmp_codigo
ISO=$1
cd $D; mkdir -p logs etapa1
estado() { echo "$(date -u +%FT%TZ) $*" | tee -a logs/etapa1.txt; }
passo() {  # nome limite comando...
  local nome=$1 limite=$2; shift 2
  estado "inicio $nome"
  timeout --kill-after=120 $limite "$@" > logs/etapa1_$nome.log 2>&1
  local rc=$?
  pkill -f "llama-server -m" 2>/dev/null; pkill -f "04_gsm8k/proxy.py" 2>/dev/null
  estado "fim $nome rc=$rc"
  return $rc
}
M="$PY medir.py --dir $D/etapa1"
S3=Qwen2.5-3B-Instruct; S7=Qwen2.5-7B-Instruct; S14=Qwen2.5-14B-Instruct

passo pip 15m $PY -m pip install math_verify "antlr4-python3-runtime==4.11" sympy
passo dados 20m $PY etapa1_baixar.py
passo oab-3b 1h $M --modelo $S3 --niveis f16 --benchmarks oab --limites oab=100
passo oab-7b 1h $M --modelo $S7 --niveis f16 --benchmarks oab --limites oab=100
passo oab-14b 90m $M --modelo $S14 --niveis f16 --benchmarks oab --limites oab=100
EXTRA=""; [ -n "$HF_TOKEN" ] && EXTRA="gpqa" && LIM_GPQA="gpqa=20"
passo 7b-q4 3h $M --modelo $S7 --niveis q4_k_m --benchmarks pubmedqa $EXTRA humaneval mbpp wmt24pp math500 --limites pubmedqa=20 $LIM_GPQA humaneval=5 mbpp=5 wmt24pp=20 math500=20

# evalplus em tmp_codigo (so se a home nao aparece no conteiner isolado); o codigo gerado NAO e executado aqui
if grep -q "No such file or directory" "$ISO" 2>/dev/null && ! grep -q "^drwx\|^total" "$ISO" 2>/dev/null; then
  mkdir -p $TMP/pkgs $TMP/cache $TMP/samples $TMP/logs $TMP/resultados_codigo $TMP/tmp
  cp pontuar_codigo.py $TMP/pontuar_codigo.py
  passo evalplus 30m bash -c "export HOME=$TMP XDG_CACHE_HOME=$TMP/cache; python3 -m pip install --target $TMP/pkgs evalplus && PYTHONPATH=$TMP/pkgs python3 -c 'from evalplus.data import get_human_eval_plus, get_mbpp_plus; print(len(get_human_eval_plus()), len(get_mbpp_plus()))'"
else
  estado "isolamento nao confirmado: evalplus nao preparado"
fi
passo avaliar 10m $PY etapa1_avaliar.py "$ISO"
estado "etapa1 terminou"
