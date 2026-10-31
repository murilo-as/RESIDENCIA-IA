# Plano de medição (prioridades 1 a 3)

Escrito em 27/10/2026, 22:00 UTC. A cadeia roda em sequência: cada job submete o próximo ao começar (`experimentos/plano.txt`, `slurm/proximo.sh`). Estimativas de término contadas a partir de 27/10 22:00 UTC, sem espera de fila.

## Como estimei

Usei a vazão já medida em `resultados.csv` (llama-server com 8 slots, hf em float16, lote 16):

| Medida de referência | Tempo |
|---|---|
| GSM8K Qwen2.5-7B f16 / q8_0 / q4_k_m | 3198 / 2180 / 1630 s |
| GSM8K Qwen2.5-14B q8_0 | 3937 s |
| MATH-500 Qwen2.5-7B f16 / q8_0 / q4_k_m | 2473 / 1536 / 1081 s |
| MATH-500 Qwen2.5-14B q8_0 | 2898 s |
| OAB (2205) Qwen2.5-7B / 14B (hf, qualquer nível) | 960 / 1900 s |
| Qwen2.5-32B f16: MMLU / MedQA / GSM8K | 927 / 363 / 11799 s |
| Qwen3-8B q4_k_m GSM8K, 153 tokens por resposta | 1446 s (~140 tokens/s agregados) |

Quantizado roda mais rápido que f16 (q8_0 ~0,7× e q4_k_m ~0,5× no GSM8K), então estimei o 32B q8_0 em 0,71× e o q4_k_m em 0,53× do f16. Para modelos sem medida usei a razão de parâmetros com o Qwen2.5-7B. A parte mais incerta é o raciocínio ligado (2.3): assumi ~1500 tokens por resposta no GSM8K e ~2800 no MATH-500, e não sei o valor real.

## Ordem e término estimado

| # | Bloco (job) | Duração | Término estimado (UTC) |
|---|---|---|---|
| **Prioridade 1** | | | |
| 1.1 | `p1-1-letra`: mmlu_letra e oab_letra no 7B f16 e validação contra o log-prob | 1 h | 27/10 23:00 |
| 1.2 | `p1-2-kv`: KV f16/q8_0/q4_0 em 7B, 14B e Qwen3-8B (pesos Q8_0) | 15 h | 28/10 14:00 |
| 1.3 | `p1-3-ancoras`: oab, pubmedqa, math500, wmt24, humaneval, mbpp nas 5 âncoras, 3 níveis | 14 h | 29/10 04:00 |
| 1.3b | `p1-pontuar` e `p1-ingerir`: evalplus no job isolado e gravação no CSV | 1 h | 29/10 05:10 |
| 1.4 | `p1-4-diag`: MMLU do Qwen3.5-9B (bf16, letra f16, letra q4_k_m) e controle no Qwen3-8B | 1 h | 29/10 06:10 |
| | `p1-resumo` → `resumo_prioridade_1.md` | 0,1 h | 29/10 06:15 |
| **Prioridade 2** | | | |
| 2.1 | `p2-1-32b`: Qwen2.5-32B-Instruct, oab/pubmedqa f16, mmlu/medqa/oab/pubmedqa/gsm8k em q8_0 e q4_k_m | 10 h | 29/10 16:15 |
| 2.2a | `p2-2-coders`: Coder 3B, 7B, 14B (download, GGUF, geração) | 3,5 h | 29/10 19:45 |
| 2.2b | `p2-2-math`: Math 1.5B e 7B com prompt de sistema CoT | 6 h | 30/10 01:45 |
| 2.2c | `p2-pontuar` e `p2-ingerir` | 1 h | 30/10 02:45 |
| 2.3 | `p2-3-raciocinio`: Qwen3-8B e Qwen3.5-9B, q4_k_m, raciocínio ligado, 4096 tokens | 15,5 h | 30/10 18:15 |
| | `p2-resumo` → `resumo_prioridade_2.md` | 0,1 h | 30/10 18:20 |
| **Prioridade 3** | | | |
| 3.1 | `p3-1-gpqa`: GPQA em 5 modelos f16 (só se o token do job e os termos do dataset permitirem) | 0,7 h | 30/10 19:00 |
| 3.2 | `p3-2-moe`: teste de vazão Qwen3-30B-A3B e Qwen3.5-35B-A3B (para aí) | 3 h | 30/10 22:00 |
| 3.3 | `p3-3-bases`: 10 bases/variantes em f16, só log-prob, máximo 2 h cada | 11 h | 31/10 09:00 |
| | `p3-resumo` → `resumo_prioridade_3.md` | 0,1 h | 31/10 09:05 |

Total estimado: ~83 h (3,5 dias). Os seus números de partida eram ~28 h para a prioridade 1 e ~22 h para a 2; minhas estimativas dão ~32 h e ~36 h. A diferença da 2 vem quase toda do raciocínio ligado (15,5 h) e do GSM8K do 32B em q8_0 e q4_k_m (4 h).

## Decisões que tomei

- **Letra por chat com 5 exemplos em turnos.** O primeiro teste, com os exemplos dentro de uma única mensagem, fez o Qwen3-1.7B responder "**Resposta:" e gastar os 4 tokens sem escrever a letra. Passei os exemplos como turnos usuário/assistente, com a instrução em português no prompt de sistema. O texto "Resposta:" que sobra é removido antes de extrair a letra.
- **Teste de 5 exemplos.** Vale para modelo ou prova que ainda não têm nenhuma linha no CSV. Passa se a acurácia for maior que zero; se der 0 em 5, tento 20 antes de reprovar. Em código, passa se alguma solução for Python sintaticamente válido (a pontuação só existe no job isolado). Raciocínio ligado conta como configuração nova e também é testado. O resultado fica em `logs/teste5.json`.
- **kv=16 reaproveita `resultados.csv`.** GSM8K e MATH-500 com KV f16 são a mesma configuração das medidas antigas, então copio essas linhas para `kv.csv` em vez de repetir. A exceção é o MATH-500 do Qwen3-8B, que ainda não existe e roda em 1.2 (a 1.3 vai repeti-lo em `resultados.csv`: ~35 min a mais, mas serve de réplica). O log-prob fp16 do diagnóstico 1.4 também é copiado.
- **KV q4_0.** Se o servidor não subir com K e V em q4_0, repito com K q4_0 e V q8_0 e gravo como `kv=k4v8`. Flash attention fica ligado em todas as medidas de KV.
- **Memória do KV.** O log do llama-server nesta versão não imprime o tamanho do cache. Gravo em `kv_memoria.csv` a fórmula da etapa 3, o tamanho do GGUF, a memória usada da máquina antes e depois de subir o servidor e o RSS do processo. No teste rápido (Qwen3-1.7B, KV q8_0, 32768 posições) a fórmula deu 1904 MiB e a memória a mais, descontado o GGUF, foi ~2,7 GiB, compatível com KV mais buffers de cálculo. O `nvidia-smi` devolve `[N/A]` neste hardware.
- **Raciocínio ligado.** Servidor com contexto 65536 (8 slots de 8192) para caber o prompt de 5 exemplos mais 4096 tokens. Os modelos de 2.3 já têm o GGUF q4_k_m.
- **Disco.** Hoje a pasta de modelos tem ~404 GB (limite do script: 450 GB). Para o 32B caber (+52 GB de q8_0 e q4_k_m), em 1.3 apago pesos e GGUFs de Qwen3-1.7B, Qwen3.5-2B e Qwen3.5-4B, que não entram em mais nenhum bloco, e só depois que todas as medidas deles estiverem registradas (`limpar.py` confere). O 32B e os especialistas também são apagados ao terminar. Qwen2.5 3B/7B/14B, Qwen3-8B e Qwen3.5-9B ficam, porque 3.1 usa os cinco.
- **GPQA.** O token é lido do `.env` dentro do job sem ser impresso nem gravado.
