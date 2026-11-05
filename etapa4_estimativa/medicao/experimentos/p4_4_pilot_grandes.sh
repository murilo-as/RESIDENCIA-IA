#!/bin/bash
# 4.4 PILOTO (supervisionar): Qwen2.5-72B-Instruct e Qwen3-Next-80B-A3B-Instruct. Objetivo: medir a vazao e ver se o disco e o llama.cpp aguentam, em q4_k_m, 100 questoes de GSM8K e 5 questoes por assunto de MMLU por letra.
# Riscos conhecidos: (1) o medir.py gera todos os niveis a partir do GGUF f16 (~145 GB para 72B; com os pesos HF e o q4 chega perto do limite de 450 GB em MAX_MODELOS); (2) o log-prob pelo hf nao roda (dequantiza para fp16): so provas por llama-server;
# (3) llama.cpp 36e36e6 pode nao rodar a arquitetura Qwen3-Next. Se (1) ou (3) falhar, o log em logs/blocos/p4_4_pilot.log diz onde. Este bloco nao apaga nada: confira o disco depois.
BLOCO=p4_4_pilot; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
marco 4
for M in Qwen2.5-72B-Instruct Qwen3-Next-80B-A3B-Instruct; do
  baixar Qwen/$M || { echo "$M: download falhou, pulado" | tee -a $LOG; continue; }
  med 6h --modelo $M --niveis q4_k_m --sem-raciocinio --benchmarks gsm8k mmlu_letra --limites gsm8k=100 mmlu_letra=5 --kv 16 --saida kv.csv
done
exit 0
