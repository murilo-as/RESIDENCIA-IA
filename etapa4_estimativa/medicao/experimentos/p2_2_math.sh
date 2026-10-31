#!/bin/bash
# 2.2 Especialistas de matematica: Qwen2.5-Math 1.5B e 7B Instruct, 3 niveis, gsm8k e math500, com o prompt de sistema da ficha do modelo (CoT): raciocinio passo a passo e resposta em \boxed{}.
# O prompt usado fica em amostras/<modelo>/<nivel>/<prova>/<data>/prompt_sistema.txt.
BLOCO=p2_2_math; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
SISTEMA='Please reason step by step, and put your final answer within \boxed{}.'
for M in Qwen2.5-Math-1.5B-Instruct Qwen2.5-Math-7B-Instruct; do
  baixar Qwen/$M || continue
  med 6h --modelo $M --benchmarks gsm8k math500 --sistema "$SISTEMA"
  limpar $M --exigir gsm8k math500
done
exit 0
