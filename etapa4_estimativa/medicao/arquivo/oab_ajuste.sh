#!/bin/bash
# Roda DENTRO do container. Conserta o OAB: instrucao em portugues + 5-shot, 100 questoes sorteadas (seed 42), f16, nos 3 modelos.
# Aceite: >= 0,35 no 7B e 14B acima do 3B. O veredito atualiza etapa1.json (chave oab).
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
cd $D; mkdir -p logs
estado() { echo "$(date -u +%FT%TZ) $*" | tee -a logs/oab_ajuste.txt; }
passo() {  # nome limite comando...
  local nome=$1 limite=$2; shift 2
  estado "inicio $nome (limite $limite)"
  timeout --kill-after=120 $limite "$@" > logs/oab_ajuste_$nome.log 2>&1
  local rc=$?
  estado "fim $nome rc=$rc"
  return $rc
}
$PY -m py_compile medir.py codigo.py pontuar_codigo.py pareado.py resumo.py baixar_modelos.py oab_avaliar.py etapa1_avaliar.py tasks/oab_exams_5shot/utils.py || { estado "ERRO de sintaxe: abortando"; exit 2; }
for M in Qwen2.5-3B-Instruct Qwen2.5-7B-Instruct Qwen2.5-14B-Instruct; do
  passo ${M%%-*}$(echo $M | cut -d- -f2) 90m $PY medir.py --dir $D/etapa1_oab --modelo $M --niveis f16 --benchmarks oab --limites oab=100
done
passo avaliar 10m $PY oab_avaliar.py
estado "oab_ajuste terminou"
