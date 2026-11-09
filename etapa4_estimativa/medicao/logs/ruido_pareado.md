# Ruido dos benchmarks: erro padrao da nota x erro padrao da diferenca pareada (f16 x q4_k_m)

EP da nota = raiz(p(1-p)/n) nas questoes comuns. EP da diferenca pareada = raiz((b + c - (b - c)^2 / n) / n^2), com b e c as questoes em que so um dos niveis acertou (mesmas questoes nos dois niveis). Dif = f16 - q4_k_m.

## Resumo por prova

| prova | modelos | EP da nota, mediana (pts) | EP da dif. pareada, mediana (pts) | razao pareado/nota | \|dif\| mediana (pts) | modelos com \|dif/EP\| > 2 |
|---|---|---|---|---|---|---|
| mmlu | 9 | 1.2 | 0.7 | 0.59 | 0.9 | 4 |
| medqa | 9 | 1.3 | 0.8 | 0.60 | 0.5 | 2 |
| oab | 9 | 1.1 | 0.7 | 0.65 | 0.9 | 3 |
| pubmedqa | 9 | 1.4 | 0.6 | 0.42 | 0.8 | 3 |
| gsm8k | 11 | 1.0 | 1.0 | 1.00 | 1.4 | 5 |
| math500 | 10 | 1.9 | 1.8 | 0.96 | 2.5 | 4 |
| humaneval_plus | 11 | 3.1 | 2.3 | 0.73 | 1.8 | 1 |
| mbpp_plus | 11 | 2.4 | 1.6 | 0.69 | 2.1 | 3 |

## Todos os modelos

| modelo | prova | n | f16 | q4_k_m | dif (pts) | EP da nota (pts) | EP da dif. pareada (pts) | dif/EP pareado |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-14B-Instruct | mmlu | 1425 | 80.6 | 80.4 | +0.1 | 1.0 | 0.5 | +0.3 |
| Qwen2.5-14B-Instruct | medqa | 1273 | 69.5 | 69.3 | +0.2 | 1.3 | 0.6 | +0.4 |
| Qwen2.5-14B-Instruct | oab | 2205 | 62.4 | 61.3 | +1.1 | 1.0 | 0.5 | +2.2 |
| Qwen2.5-14B-Instruct | pubmedqa | 1000 | 78.4 | 78.0 | +0.4 | 1.3 | 0.4 | +0.9 |
| Qwen2.5-14B-Instruct | gsm8k | 1319 | 85.5 | 86.7 | -1.2 | 1.0 | 0.8 | -1.6 |
| Qwen2.5-14B-Instruct | math500 | 500 | 77.6 | 74.4 | +3.2 | 1.9 | 1.5 | +2.1 |
| Qwen2.5-14B-Instruct | humaneval_plus | 164 | 76.8 | 79.3 | -2.4 | 3.3 | 2.3 | -1.1 |
| Qwen2.5-14B-Instruct | mbpp_plus | 378 | 73.8 | 69.8 | +4.0 | 2.3 | 1.6 | +2.4 |
| Qwen2.5-32B-Instruct | mmlu | 1425 | 83.9 | 83.0 | +0.9 | 1.0 | 0.4 | +2.0 |
| Qwen2.5-32B-Instruct | medqa | 1273 | 72.6 | 72.2 | +0.4 | 1.3 | 0.6 | +0.7 |
| Qwen2.5-32B-Instruct | oab | 2205 | 63.1 | 62.5 | +0.6 | 1.0 | 0.4 | +1.4 |
| Qwen2.5-32B-Instruct | pubmedqa | 1000 | 79.4 | 80.3 | -0.9 | 1.3 | 0.4 | -2.5 |
| Qwen2.5-32B-Instruct | gsm8k | 1319 | 84.5 | 85.0 | -0.5 | 1.0 | 0.6 | -0.8 |
| Qwen2.5-3B-Instruct | mmlu | 1425 | 69.8 | 67.1 | +2.7 | 1.2 | 0.8 | +3.4 |
| Qwen2.5-3B-Instruct | medqa | 1273 | 51.1 | 50.9 | +0.2 | 1.4 | 0.9 | +0.3 |
| Qwen2.5-3B-Instruct | oab | 2205 | 49.7 | 46.8 | +2.9 | 1.1 | 0.7 | +4.0 |
| Qwen2.5-3B-Instruct | pubmedqa | 1000 | 73.4 | 73.4 | +0.0 | 1.4 | 0.7 | +0.0 |
| Qwen2.5-3B-Instruct | gsm8k | 1319 | 76.1 | 72.9 | +3.3 | 1.2 | 1.0 | +3.3 |
| Qwen2.5-3B-Instruct | math500 | 500 | 64.0 | 62.8 | +1.2 | 2.1 | 1.9 | +0.6 |
| Qwen2.5-3B-Instruct | humaneval_plus | 164 | 67.1 | 62.2 | +4.9 | 3.7 | 3.2 | +1.5 |
| Qwen2.5-3B-Instruct | mbpp_plus | 378 | 54.5 | 61.4 | -6.9 | 2.6 | 2.5 | -2.8 |
| Qwen2.5-7B-Instruct | mmlu | 1425 | 75.7 | 75.3 | +0.4 | 1.1 | 0.6 | +0.8 |
| Qwen2.5-7B-Instruct | medqa | 1273 | 62.2 | 60.7 | +1.5 | 1.4 | 0.7 | +2.0 |
| Qwen2.5-7B-Instruct | oab | 2205 | 53.5 | 52.3 | +1.2 | 1.1 | 0.6 | +2.0 |
| Qwen2.5-7B-Instruct | pubmedqa | 1000 | 75.6 | 75.9 | -0.3 | 1.4 | 0.6 | -0.5 |
| Qwen2.5-7B-Instruct | gsm8k | 1319 | 85.1 | 85.7 | -0.7 | 1.0 | 0.8 | -0.8 |
| Qwen2.5-7B-Instruct | math500 | 500 | 75.4 | 73.4 | +2.0 | 1.9 | 1.6 | +1.3 |
| Qwen2.5-7B-Instruct | humaneval_plus | 164 | 78.7 | 76.8 | +1.8 | 3.2 | 2.5 | +0.7 |
| Qwen2.5-7B-Instruct | mbpp_plus | 378 | 70.4 | 68.8 | +1.6 | 2.3 | 1.3 | +1.2 |
| Qwen2.5-Coder-14B-Instruct | humaneval_plus | 164 | 86.6 | 87.8 | -1.2 | 2.7 | 1.2 | -1.0 |
| Qwen2.5-Coder-14B-Instruct | mbpp_plus | 378 | 75.1 | 74.6 | +0.5 | 2.2 | 1.1 | +0.5 |
| Qwen2.5-Coder-3B-Instruct | humaneval_plus | 164 | 79.9 | 78.7 | +1.2 | 3.1 | 1.7 | +0.7 |
| Qwen2.5-Coder-3B-Instruct | mbpp_plus | 378 | 63.8 | 61.9 | +1.9 | 2.5 | 1.4 | +1.3 |
| Qwen2.5-Coder-7B-Instruct | humaneval_plus | 164 | 80.5 | 85.4 | -4.9 | 3.1 | 2.1 | -2.3 |
| Qwen2.5-Coder-7B-Instruct | mbpp_plus | 378 | 69.8 | 70.9 | -1.1 | 2.4 | 1.5 | -0.7 |
| Qwen2.5-Math-1.5B-Instruct | gsm8k | 1319 | 76.4 | 71.8 | +4.6 | 1.2 | 1.0 | +4.4 |
| Qwen2.5-Math-1.5B-Instruct | math500 | 500 | 52.0 | 53.2 | -1.2 | 2.2 | 1.9 | -0.6 |
| Qwen2.5-Math-7B-Instruct | gsm8k | 1319 | 90.4 | 89.5 | +1.0 | 0.8 | 0.6 | +1.6 |
| Qwen2.5-Math-7B-Instruct | math500 | 500 | 79.8 | 78.8 | +1.0 | 1.8 | 1.4 | +0.7 |
| Qwen3-1.7B | mmlu | 1425 | 63.6 | 62.7 | +0.9 | 1.3 | 0.9 | +1.0 |
| Qwen3-1.7B | medqa | 1273 | 42.3 | 43.4 | -1.1 | 1.4 | 1.1 | -1.0 |
| Qwen3-1.7B | oab | 2205 | 40.6 | 40.8 | -0.2 | 1.0 | 0.8 | -0.2 |
| Qwen3-1.7B | pubmedqa | 1000 | 72.3 | 73.2 | -0.9 | 1.4 | 1.0 | -0.9 |
| Qwen3-1.7B | gsm8k | 1319 | 73.5 | 67.0 | +6.4 | 1.2 | 1.3 | +5.1 |
| Qwen3-1.7B | math500 | 500 | 67.2 | 60.0 | +7.2 | 2.1 | 1.9 | +3.8 |
| Qwen3-1.7B | humaneval_plus | 164 | 61.0 | 54.9 | +6.1 | 3.8 | 3.6 | +1.7 |
| Qwen3-1.7B | mbpp_plus | 378 | 46.8 | 49.2 | -2.4 | 2.6 | 2.3 | -1.0 |
| Qwen3-8B | mmlu | 1425 | 77.8 | 77.3 | +0.6 | 1.1 | 0.6 | +0.9 |
| Qwen3-8B | medqa | 1273 | 64.1 | 64.1 | +0.0 | 1.3 | 0.8 | +0.0 |
| Qwen3-8B | oab | 2205 | 54.1 | 53.2 | +0.9 | 1.1 | 0.7 | +1.4 |
| Qwen3-8B | pubmedqa | 1000 | 77.1 | 77.2 | -0.1 | 1.3 | 0.4 | -0.2 |
| Qwen3-8B | gsm8k | 1319 | 84.5 | 90.1 | -5.6 | 1.0 | 1.0 | -5.5 |
| Qwen3-8B | math500 | 500 | 79.6 | 68.6 | +11.0 | 1.8 | 1.8 | +6.3 |
| Qwen3-8B | humaneval_plus | 164 | 79.9 | 79.3 | +0.6 | 3.1 | 2.0 | +0.3 |
| Qwen3-8B | mbpp_plus | 378 | 71.2 | 68.8 | +2.4 | 2.3 | 1.5 | +1.6 |
| Qwen3.5-2B | mmlu | 1425 | 59.4 | 57.6 | +1.8 | 1.3 | 0.8 | +2.3 |
| Qwen3.5-2B | medqa | 1273 | 47.6 | 47.1 | +0.5 | 1.4 | 1.0 | +0.5 |
| Qwen3.5-2B | oab | 2205 | 46.8 | 45.4 | +1.4 | 1.1 | 0.7 | +2.0 |
| Qwen3.5-2B | pubmedqa | 1000 | 73.3 | 74.1 | -0.8 | 1.4 | 0.7 | -1.1 |
| Qwen3.5-2B | gsm8k | 1319 | 70.4 | 68.9 | +1.4 | 1.3 | 1.3 | +1.1 |
| Qwen3.5-2B | math500 | 500 | 62.0 | 59.0 | +3.0 | 2.2 | 2.0 | +1.5 |
| Qwen3.5-2B | humaneval_plus | 164 | 48.2 | 47.0 | +1.2 | 3.9 | 3.1 | +0.4 |
| Qwen3.5-2B | mbpp_plus | 378 | 49.5 | 42.1 | +7.4 | 2.6 | 2.3 | +3.2 |
| Qwen3.5-4B | mmlu | 1425 | 71.2 | 70.9 | +0.3 | 1.2 | 0.7 | +0.4 |
| Qwen3.5-4B | medqa | 1273 | 70.7 | 68.9 | +1.8 | 1.3 | 0.8 | +2.2 |
| Qwen3.5-4B | oab | 2205 | 54.5 | 55.1 | -0.6 | 1.1 | 0.8 | -0.8 |
| Qwen3.5-4B | pubmedqa | 1000 | 78.1 | 75.7 | +2.4 | 1.3 | 0.6 | +3.9 |
| Qwen3.5-4B | gsm8k | 1319 | 90.9 | 89.8 | +1.1 | 0.8 | 0.7 | +1.5 |
| Qwen3.5-4B | math500 | 500 | 81.8 | 81.0 | +0.8 | 1.7 | 1.4 | +0.6 |
| Qwen3.5-4B | humaneval_plus | 164 | 79.9 | 76.8 | +3.0 | 3.1 | 2.6 | +1.2 |
| Qwen3.5-4B | mbpp_plus | 378 | 67.7 | 69.6 | -1.9 | 2.4 | 1.6 | -1.1 |
| Qwen3.5-9B | mmlu | 1425 | 68.7 | 71.9 | -3.2 | 1.2 | 0.7 | -4.4 |
| Qwen3.5-9B | medqa | 1273 | 75.2 | 74.0 | +1.2 | 1.2 | 0.8 | +1.5 |
| Qwen3.5-9B | oab | 2205 | 60.3 | 59.7 | +0.6 | 1.0 | 0.7 | +0.8 |
| Qwen3.5-9B | pubmedqa | 1000 | 75.2 | 73.7 | +1.5 | 1.4 | 0.6 | +2.6 |
| Qwen3.5-9B | gsm8k | 1319 | 94.2 | 49.2 | +45.0 | 0.6 | 1.4 | +31.5 |
| Qwen3.5-9B | math500 | 500 | 85.2 | 32.4 | +52.8 | 1.6 | 2.2 | +23.6 |
| Qwen3.5-9B | humaneval_plus | 164 | 82.3 | 81.7 | +0.6 | 3.0 | 2.2 | +0.3 |
| Qwen3.5-9B | mbpp_plus | 378 | 73.8 | 71.7 | +2.1 | 2.3 | 1.7 | +1.3 |

## Sem comparacao

- Qwen2.5-32B-Instruct math500: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-32B
- Qwen2.5-32B-Instruct humaneval_plus: sem /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-32B-Instruct/f1
- Qwen2.5-32B-Instruct mbpp_plus: sem /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-32B-Instruct/f1
- Qwen2.5-Coder-14B-Instruct mmlu: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-14B-Instruct medqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-14B-Instruct oab: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-14B-Instruct pubmedqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-14B-Instruct gsm8k: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-14B-Instruct math500: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-3B-Instruct mmlu: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-3B-Instruct medqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-3B-Instruct oab: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-3B-Instruct pubmedqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-3B-Instruct gsm8k: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-3B-Instruct math500: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-7B-Instruct mmlu: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-7B-Instruct medqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-7B-Instruct oab: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-7B-Instruct pubmedqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-7B-Instruct gsm8k: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Coder-7B-Instruct math500: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Cod
- Qwen2.5-Math-1.5B-Instruct mmlu: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Mat
- Qwen2.5-Math-1.5B-Instruct medqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Mat
- Qwen2.5-Math-1.5B-Instruct oab: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Mat
- Qwen2.5-Math-1.5B-Instruct pubmedqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Mat
- Qwen2.5-Math-1.5B-Instruct humaneval_plus: sem /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Math-1.5B-Instr
- Qwen2.5-Math-1.5B-Instruct mbpp_plus: sem /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Math-1.5B-Instr
- Qwen2.5-Math-7B-Instruct mmlu: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Mat
- Qwen2.5-Math-7B-Instruct medqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Mat
- Qwen2.5-Math-7B-Instruct oab: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Mat
- Qwen2.5-Math-7B-Instruct pubmedqa: sem amostras em /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Mat
- Qwen2.5-Math-7B-Instruct humaneval_plus: sem /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Math-7B-Instruc
- Qwen2.5-Math-7B-Instruct mbpp_plus: sem /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/amostras/Qwen2.5-Math-7B-Instruc

## Diagnostico: MBPP+ do Qwen2.5-3B-Instruct

| nivel | n | base | plus | base=0 (nem o teste simples passa) | base ok e plus falha | cortadas | tokens/resposta |
|---|---|---|---|---|---|---|---|
| f16 | 378 | 245 | 206 | 133 | 39 | 1 | 211 |
| q8_0 | 378 | 212 | 181 | 166 | 31 | 1 | 210 |
| q4_k_m | 378 | 274 | 232 | 104 | 42 | 0 | 165 |

Pareado por questao (mbpp_plus):

| A | B | n | acc A | acc B | dif (pts) | so A acertou | so B acertou | EP da dif. (pts) | dif/EP |
|---|---|---|---|---|---|---|---|---|---|
| f16 | q4_k_m | 378 | 54.5 | 61.4 | -6.9 | 32 | 58 | 2.5 | -2.8 |
| f16 | q8_0 | 378 | 54.5 | 47.9 | +6.6 | 34 | 9 | 1.7 | +3.9 |
| q8_0 | q4_k_m | 378 | 47.9 | 61.4 | -13.5 | 32 | 83 | 2.8 | -4.9 |

Das 378 questoes, 142 passam nos 3 niveis, 112 falham nos 3 e 124 divergem entre niveis.

### Leitura (feita à mão sobre os números acima; `base` e `plus` são contagens de questões)

- **Não é falha de extração visível.** Nos 3 níveis quase não há respostas cortadas (1, 1, 0) e o tamanho médio é parecido (211, 210, 166 tokens). Mas o código gerado não fica guardado em `amostras/` (só a pontuação por questão), então não dá para separar "código não extraído" de "código errado" olhando as respostas. Para fechar isso é preciso gravar o código gerado de uma execução.
- **A queda de −12,6 a −13,5 pts aparece entre q8_0 e q4_k_m** (47,9 contra 61,4), não entre f16 e q4_k_m (54,5 contra 61,4, em que q4_k_m *sobe* 6,9). Os três níveis não são monotônicos: q8_0 < f16 < q4_k_m. A diferença q8_0 × q4_k_m é de 4,9 erros padrão pareados (83 questões só o q4 acerta, 32 só o q8).
- **Muita instabilidade entre níveis:** de 378 questões, 142 passam nos 3 níveis, 112 falham nos 3 e **124 (33%) divergem**. Com temperatura 0 a quantização muda a trajetória e o programa gerado, e no 3B isso pesa mais que a perda média de acurácia. Também são 133, 166 e 104 questões em que nem o teste simples (`base`) passa.
- **Conclusão:** é diferença real de acerto em cada nível (não é ruído de amostragem, que está em ~2,5 pts), mas sem relação com bits. Para o estimador, a razão q4/f16 de um modelo pequeno de código não deve ser lida como efeito da quantização; a incerteza de uma razão assim é de ±6 a 10 pts, não os 2,5 pts do erro padrão da nota.
