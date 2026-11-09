#!/bin/bash
# P2-d Ancoras grandes (9 provas x 3 niveis, raciocinio desligado): Qwen3-30B-A3B, Qwen3.5-35B-A3B (MoE) e Qwen3.5-27B. Uso: p4_8_ancoras_grandes.sh MODELO... (um job por modelo: cada job da particao tem no maximo 2 dias).
# Qwen3.5-*: acrescenta mmlu_letra nos 3 niveis (kv=16, kv.csv; o estimador usa o MMLU por letra em todos os Qwen3.5 pos-treino).
# Qwen3-30B-A3B: se o log-prob (hf) falhar (o Base deu OOM em f16), refaz com --batch-hf 1 antes de pular; se ainda falhar, registra em erros.log e mede mmlu_letra pelo llama-server.
# Apaga o modelo ao terminar (limpar.py confere).
BLOCO=p4_8_grandes_${1//[^A-Za-z0-9.]/_}; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
LP="mmlu medqa oab pubmedqa"   # provas por log-prob
faltam_lp() { local f=""; for B in $LP; do grep -q "^$1,f16,$B," resultados.csv || f="$f $B"; done; echo $f; }
for M in "$@"; do
  usado=$(du -s --block-size=1G /beegfs/home/user_muriloalves/work/models | cut -f1)
  if [ "$usado" -gt 250 ]; then echo "$M: pasta de modelos com ${usado} GB (precisa de ~200 GB livres dentro do limite de 450); pulado" | tee -a $LOG | tee -a erros.log; continue; fi
  baixar Qwen/$M || { echo "$M: download falhou, pulado" | tee -a $LOG; continue; }
  med 20h --modelo $M --sem-raciocinio --benchmarks mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp
  EXIGIR="mmlu medqa oab pubmedqa gsm8k math500 wmt24 humaneval mbpp"
  case $M in
    Qwen3.5-*)
      med 4h --modelo $M --niveis f16 q8_0 q4_k_m --kv 16 --saida kv.csv --benchmarks mmlu_letra
      EXIGIR="$EXIGIR mmlu_letra" ;;
    Qwen3-30B-A3B)
      F=$(faltam_lp $M)
      if [ -n "$F" ]; then
        echo "$(date -u +%FT%TZ) $M: log-prob falhou em f16 ($F); repetindo com --batch-hf 1" | tee -a $LOG
        $PY - <<'PYEOF'
import json, os
p = "logs/teste5.json"
d = json.load(open(p))
ks = [k for k, v in d.items() if k.startswith("Qwen3-30B-A3B|") and k.split("|")[1] in ("mmlu", "medqa", "oab", "pubmedqa") and not v["ok"]]
for k in ks: d.pop(k)
json.dump(d, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
print("teste de 5 exemplos apagado para repetir:", ks)
PYEOF
        med 8h --modelo $M --batch-hf 1 --benchmarks $F
        F=$(faltam_lp $M)
      fi
      if [ -n "$F" ]; then
        echo "$(date -u +%FT%TZ) $M: log-prob falhou mesmo com --batch-hf 1 em:$F; registrado como falhou; medindo mmlu_letra pelo llama-server" | tee -a $LOG | tee -a erros.log
        med 4h --modelo $M --niveis f16 q8_0 q4_k_m --kv 16 --saida kv.csv --benchmarks mmlu_letra
        EXIGIR="gsm8k math500 wmt24 humaneval mbpp mmlu_letra"
      fi ;;
  esac
  limpar $M --exigir $EXIGIR
done
exit 0
