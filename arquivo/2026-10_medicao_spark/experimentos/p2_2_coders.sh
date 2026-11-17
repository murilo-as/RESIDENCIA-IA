#!/bin/bash
# 2.2 Especialistas de codigo: Qwen2.5-Coder 3B, 7B e 14B Instruct, 3 niveis, humaneval_plus e mbpp_plus (gerar aqui, pontuar no job isolado). Um modelo por vez; apaga ao terminar a geracao.
BLOCO=p2_2_coders; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
for M in Qwen2.5-Coder-3B-Instruct Qwen2.5-Coder-7B-Instruct Qwen2.5-Coder-14B-Instruct; do
  baixar Qwen/$M || continue
  med 5h --modelo $M --benchmarks humaneval mbpp
  limpar $M --exigir humaneval mbpp
done
exit 0
