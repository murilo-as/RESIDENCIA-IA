
## Qwen3.5-35B-A3B q4_k_m (2026-10-31T00:18:04Z)

- GGUF q4_k_m: 21.7 GB
- llama-bench (pp512 e tg128, tokens/s):
```
| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| qwen35moe 35B.A3B Q4_K - Medium |  20.21 GiB |    35.51 B | CUDA       |  99 |           pp512 |     2595.88 ± 244.56 |
| qwen35moe 35B.A3B Q4_K - Medium |  20.21 GiB |    35.51 B | CUDA       |  99 |           tg128 |         82.35 ± 0.15 |

build: 36e36e6 (1)
```
- GSM8K 20 questoes pelo llama-server: 92 s (acc 0.95, 152.6 tokens/resposta). Estimativa do GSM8K completo (1319) em q4_k_m: 1.7 h
- MMLU 114 questoes pelo hf (2 por assunto, sem contar a carga do modelo): 76 s. Estimativa do MMLU de 1425 questoes: 16 min por nivel
- Ancoras inteiras (mmlu, medqa, gsm8k, oab, pubmedqa, math500, wmt24, codigo em 3 niveis): usar as estimativas acima e a razao dos tempos do Qwen2.5-7B (ver plano_medicao.md); nao foram rodadas.
