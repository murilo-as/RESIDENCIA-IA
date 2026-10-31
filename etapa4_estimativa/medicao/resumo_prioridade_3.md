# Prioridade 3: resumo

Periodo: 2026-10-30T22:58:32Z a 2026-10-31T09:26:24Z (gerado em 2026-10-31T09:26:24Z).

## Linhas novas

### resultados.csv (36 linhas)

| modelo | nivel | benchmark | n | acuracia | erro_padrao | tempo_s | tokens_por_resposta | cortadas |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-3B | f16 | mmlu | 1425 | 0.686316 | 0.0118 | 142.3 |  |  |
| Qwen2.5-3B | f16 | medqa | 1273 | 0.499607 | 0.014019 | 38.8 |  |  |
| Qwen2.5-3B | f16 | oab | 2205 | 0.510658 | 0.010648 | 582.7 |  |  |
| Qwen2.5-3B | f16 | pubmedqa | 1000 | 0.733 | 0.013997 | 48.8 |  |  |
| Qwen2.5-7B | f16 | mmlu | 1425 | 0.761404 | 0.010892 | 246.8 |  |  |
| Qwen2.5-7B | f16 | medqa | 1273 | 0.641005 | 0.01345 | 75.9 |  |  |
| Qwen2.5-7B | f16 | oab | 2205 | 0.556463 | 0.010582 | 1029.1 |  |  |
| Qwen2.5-7B | f16 | pubmedqa | 1000 | 0.764 | 0.013434 | 89.5 |  |  |
| Qwen3-1.7B-Base | f16 | mmlu | 1425 | 0.655439 | 0.012209 | 96.0 |  |  |
| Qwen3-1.7B-Base | f16 | medqa | 1273 | 0.468971 | 0.013992 | 42.2 |  |  |
| Qwen3-1.7B-Base | f16 | oab | 2205 | 0.435374 | 0.010561 | 481.5 |  |  |
| Qwen3-1.7B-Base | f16 | pubmedqa | 1000 | 0.715 | 0.014282 | 38.1 |  |  |
| Qwen3.5-2B-Base | f16 | mmlu | 1425 | 0.552281 | 0.012708 | 154.9 |  |  |
| Qwen3.5-2B-Base | f16 | medqa | 1273 | 0.480754 | 0.014009 | 60.6 |  |  |
| Qwen3.5-2B-Base | f16 | oab | 2205 | 0.468934 | 0.01063 | 624.8 |  |  |
| Qwen3.5-2B-Base | f16 | pubmedqa | 1000 | 0.738 | 0.013912 | 59.7 |  |  |
| Qwen3.5-4B-Base | f16 | mmlu | 1425 | 0.756491 | 0.010926 | 365.8 |  |  |
| Qwen3.5-4B-Base | f16 | medqa | 1273 | 0.672427 | 0.013159 | 110.7 |  |  |
| Qwen3.5-4B-Base | f16 | oab | 2205 | 0.586395 | 0.01049 | 1345.4 |  |  |
| Qwen3.5-4B-Base | f16 | pubmedqa | 1000 | 0.769 | 0.013335 | 135.7 |  |  |
| Qwen3-8B-Base | f16 | mmlu | 1425 | 0.790877 | 0.010268 | 325.3 |  |  |
| Qwen3-8B-Base | f16 | medqa | 1273 | 0.65436 | 0.013335 | 92.7 |  |  |
| Qwen3-8B-Base | f16 | oab | 2205 | 0.573243 | 0.010535 | 1306.5 |  |  |
| Qwen3-8B-Base | f16 | pubmedqa | 1000 | 0.772 | 0.013274 | 118.0 |  |  |
| Qwen3.5-9B-Base | f16 | mmlu | 1425 | 0.727719 | 0.011456 | 478.8 |  |  |
| Qwen3.5-9B-Base | f16 | medqa | 1273 | 0.729772 | 0.012451 | 141.1 |  |  |
| Qwen3.5-9B-Base | f16 | oab | 2205 | 0.63356 | 0.010263 | 1734.2 |  |  |
| Qwen3.5-9B-Base | f16 | pubmedqa | 1000 | 0.789 | 0.012909 | 200.7 |  |  |
| Qwen2.5-14B | f16 | mmlu | 1425 | 0.81193 | 0.009959 | 462.3 |  |  |
| Qwen2.5-14B | f16 | medqa | 1273 | 0.688924 | 0.01298 | 145.5 |  |  |
| Qwen2.5-14B | f16 | oab | 2205 | 0.631746 | 0.010274 | 2131.8 |  |  |
| Qwen2.5-14B | f16 | pubmedqa | 1000 | 0.778 | 0.013149 | 220.4 |  |  |
| Qwen3.6-35B-A3B | f16 | mmlu | 1425 | 0.82807 | 0.0094 | 565.5 |  |  |
| Qwen3.6-35B-A3B | f16 | medqa | 1273 | 0.864101 | 0.009608 | 229.4 |  |  |
| Qwen3.6-35B-A3B | f16 | oab | 2205 | 0.693424 | 0.009821 | 1859.9 |  |  |
| Qwen3.6-35B-A3B | f16 | pubmedqa | 1000 | 0.732 | 0.014013 | 244.4 |  |  |

### vazao_moe.csv (5 linhas)

| modelo | nivel | benchmark | n | acuracia | erro_padrao | tempo_s | tokens_por_resposta | cortadas |
|---|---|---|---|---|---|---|---|---|
| Qwen3-30B-A3B | q4_k_m | gsm8k | 20 | 0.95 | 0.05 | 98.2 | 156.7 | 0 |
| Qwen3-30B-A3B | q4_k_m | gsm8k_strict | 20 | 0.95 | 0.05 | 98.2 | 156.7 | 0 |
| Qwen3.5-35B-A3B | q4_k_m | gsm8k | 20 | 0.95 | 0.05 | 92.0 | 152.6 | 0 |
| Qwen3.5-35B-A3B | q4_k_m | gsm8k_strict | 20 | 0.95 | 0.05 | 92.0 | 152.6 | 0 |
| Qwen3.5-35B-A3B | q4_k_m | mmlu | 114 | 0.885965 | 0.029093 | 75.6 |  |  |

## Erros (erros.log)

```
2026-10-31T07:41:11Z Qwen3-30B-A3B-Base f16 mmlu: teste de 5 exemplos reprovou, prova pulada: erro no teste: rojects/RESIDENCIA-IA/piloto/venv/lib/python3.12/site-packages/transformers/modeling_utils.py", line 4353, in from_pretrained

```

Testes de 5 exemplos no periodo: 37 (1 reprovados)
- reprovado Qwen3-30B-A3B-Base|mmlu: erro no teste: rojects/RESIDENCIA-IA/piloto/venv/lib/python3.12/site-packages/transformers/modeling_utils.py", line 4353, in from_pretrained
    loading_info, disk_offload_index = cls._load_pretrained

## Anomalias

(nenhuma regra de anomalia disparou)


## Tempos

Soma de tempo_s por prova (so o tempo medido, sem carga de modelo nem montagem das tarefas): gsm8k 0.05 h, gsm8k_strict 0.05 h, medqa 0.26 h, mmlu 0.81 h, oab 3.08 h, pubmedqa 0.32 h

| bloco | chamada | duracao | rc |
|---|---|---|---|
| p3_3_bases | --modelo Qwen2.5-3B --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 0.42 h | 0 |
| p3_3_bases | --modelo Qwen2.5-7B --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 0.66 h | 0 |
| p3_3_bases | --modelo Qwen3-1.7B-Base --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 0.40 h | 0 |
| p3_3_bases | --modelo Qwen3.5-2B-Base --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 0.44 h | 0 |
| p3_3_bases | --modelo Qwen3.5-4B-Base --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 0.78 h | 0 |
| p3_3_bases | --modelo Qwen3-8B-Base --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 0.76 h | 0 |
| p3_3_bases | --modelo Qwen3.5-9B-Base --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 0.96 h | 0 |
| p3_3_bases | --modelo Qwen2.5-14B --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 1.19 h | 0 |
| p3_3_bases | --modelo Qwen3-30B-A3B-Base --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 0.66 h | 137 |
| p3_3_bases | --modelo Qwen3.6-35B-A3B --niveis f16 --batch-hf 4 --benchmarks mmlu medqa oab pubmedqa | 1.19 h | 0 |

## 3.1 Acesso ao GPQA

falha: DatasetNotFoundError (termos do dataset nao aceitos, token sem acesso ou sem rede; mensagem omitida)

## 3.2 Vazao dos MoE

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

## Pendencias

Ver a secao de erros acima e `erros.log`; provas puladas pelo teste de 5 exemplos aparecem em `logs/teste5.json`.

