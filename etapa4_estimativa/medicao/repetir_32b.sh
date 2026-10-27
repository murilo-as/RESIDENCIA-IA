#!/bin/bash
# Roda DENTRO do container. Repete o Qwen2.5-32B f16: o job 924 morreu (Killed, falta de memoria) no MMLU com batch 16.
# GSM8K primeiro (llama-server, nao usa o hf); depois MMLU e MedQA com batch pequeno.
D=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao
PY=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
cd $D; mkdir -p logs
echo "$(date -u +%FT%TZ) inicio 32b gsm8k" | tee -a logs/repetir_32b.txt
timeout --kill-after=120 6h $PY medir.py --modelo Qwen2.5-32B-Instruct --niveis f16 --benchmarks gsm8k > logs/repetir_32b_gsm8k.log 2>&1
echo "$(date -u +%FT%TZ) fim 32b gsm8k rc=$?" | tee -a logs/repetir_32b.txt
pkill -f "llama-server -m" 2>/dev/null
echo "$(date -u +%FT%TZ) inicio 32b mmlu medqa (batch-hf 2)" | tee -a logs/repetir_32b.txt
timeout --kill-after=120 3h $PY medir.py --modelo Qwen2.5-32B-Instruct --niveis f16 --benchmarks mmlu medqa --batch-hf 2 > logs/repetir_32b_hf.log 2>&1
echo "$(date -u +%FT%TZ) fim 32b mmlu medqa rc=$?" | tee -a logs/repetir_32b.txt
exit 0
