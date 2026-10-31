#!/bin/bash
# 3.2 MoE, so um teste de vazao em q4_k_m (llama-bench, 20 questoes de GSM8K, mmlu --limit 2 pelo hf). Relata em vazao_moe.md e PARA: nao roda as ancoras.
BLOCO=p3_2_moe; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen3-30B-A3B Qwen3.5-35B-A3B; do
  baixar Qwen/$M || { echo "$M: download falhou" | tee -a $LOG; continue; }
  timeout --kill-after=120 3h $PY experimentos/moe_vazao.py $M >> logs/blocos/$BLOCO.log 2>&1
  echo "$(date -u +%FT%TZ) moe_vazao $M rc=$?" | tee -a $LOG
  pkill -f "llama-server -m" 2>/dev/null; sleep 5
  MD=/beegfs/home/user_muriloalves/work/models; L=$(echo $M | tr 'A-Z' 'a-z')  # so teste de vazao: nao e reusado; nomes exatos (nao pega o -Base)
  [ -n "$M" ] && rm -rf $MD/$M $MD/$L-f16.gguf $MD/$L-f16.gguf.parcial $MD/$L-q4_k_m.gguf $MD/$L-q4_k_m.gguf.parcial
done
exit 0
