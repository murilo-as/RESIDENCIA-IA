#!/bin/bash
# Qwen3.5-27B e Qwen3-30B-A3B em partes (14-16/11: o vigia-memoria matou os jobs 1614 e 1617 no log-prob f16; nada foi medido). Uso: p4_11_grandes_divididos.sh MODELO
# 1) provas por geracao (llama-server) nos 3 niveis; 2) mmlu_letra (kv.csv; sempre nos Qwen3.5; no 30B so se o log-prob falhar); 3) log-prob (mmlu medqa oab pubmedqa) um nivel por vez, f16 por ultimo,
# com --batch-hf 1: se o f16 for morto, q8_0 e q4_k_m ja estao nos CSVs e a falha vai para erros.log. limpar so apaga se tudo o que sobrou estiver registrado.
BLOCO=p4_11_${1//[^A-Za-z0-9.]/_}; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
M=$1; LP="mmlu medqa oab pubmedqa"; GEN="gsm8k math500 wmt24 humaneval mbpp"
faltam() { local f=""; for B in $LP; do grep -q "^$M,$1,$B," resultados.csv || f="$f $B"; done; echo $f; }
usado=$(du -s --block-size=1G /beegfs/home/user_muriloalves/work/models | cut -f1)
if [ "$usado" -gt 300 ]; then echo "$M: pasta de modelos com ${usado} GB; pulado" | tee -a $LOG | tee -a erros.log; exit 0; fi
baixar Qwen/$M || { echo "$M: download falhou, pulado" | tee -a $LOG; exit 0; }
med 20h --modelo $M --sem-raciocinio --benchmarks $GEN
case $M in Qwen3.5-*) med 4h --modelo $M --niveis f16 q8_0 q4_k_m --kv 16 --saida kv.csv --benchmarks mmlu_letra; LETRA=1 ;; esac
for N in q4_k_m q8_0 f16; do
  F=$(faltam $N)
  [ -n "$F" ] && med 6h --modelo $M --niveis $N --batch-hf 1 --sem-raciocinio --benchmarks $F
done
EXIGIR="$GEN"; FALTA=""
for B in $LP; do
  ok=1; for N in f16 q8_0 q4_k_m; do grep -q "^$M,$N,$B," resultados.csv || ok=0; done
  [ $ok = 1 ] && EXIGIR="$EXIGIR $B" || FALTA="$FALTA $B"
done
if [ -n "$FALTA" ]; then
  echo "$(date -u +%FT%TZ) $M: log-prob falhou em$FALTA (ver vigia-memoria nos .err); registrado como falhou" | tee -a $LOG | tee -a erros.log
  [ -z "$LETRA" ] && { med 4h --modelo $M --niveis f16 q8_0 q4_k_m --kv 16 --saida kv.csv --benchmarks mmlu_letra; LETRA=1; }
fi
[ -n "$LETRA" ] && EXIGIR="$EXIGIR mmlu_letra"
limpar $M --exigir $EXIGIR
exit 0
