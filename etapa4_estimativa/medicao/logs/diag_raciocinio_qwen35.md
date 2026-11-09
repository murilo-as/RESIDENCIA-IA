# P2-a Diagnóstico: raciocínio ligado do Qwen3.5-9B (q4_k_m, limite de 4096 tokens)

Só leitura de `amostras/` (os `proxy.jsonl` de cada execução e os `samples_*.jsonl` do lm-eval). Nenhum resultado foi alterado. Executado em 05/11/2026.

## Resultado em `raciocinio.csv`

| modelo | prova | n | acurácia | tokens/resposta | cortadas (`cortadas`) |
|---|---|---|---|---|---|
| Qwen3.5-9B | gsm8k | 1319 | 0,492 | 2168 | 197 (14,9%) |
| Qwen3.5-9B | math500 | 500 | 0,324 | 2257 | 148 (29,6%) |
| Qwen3-8B (controle) | gsm8k | 1319 | 0,901 | 843 | 39 (3,0%) |
| Qwen3-8B (controle) | math500 | 500 | 0,686 | 2670 | 158 (31,6%) |

## O que mostram os arquivos

`finish_reason` de cada chamada (`proxy.jsonl`) e tamanho do texto devolvido (`resps` do lm-eval, que é o `content` do llama-server):

| modelo | prova | n | finish=length | resposta vazia | vazia e finish≠length (estimativa) | acerto entre as não vazias |
|---|---|---|---|---|---|---|
| Qwen3.5-9B | gsm8k | 1319 | 197 | **640 (48,5%)** | ~443 | 649 / 679 = **95,6%** |
| Qwen3.5-9B | math500 | 500 | 148 | **327 (65,4%)** | ~179 | 162 / 173 = **93,6%** |
| Qwen3-8B | gsm8k | 1319 | 39 | 36 (2,7%) | ~0 | 1189 / 1283 = 92,7% |
| Qwen3-8B | math500 | 500 | 158 | 132 (26,4%) | 0 | 343 / 368 = 93,2% |

(Acertos do MATH-500 = nota `math_verify` do CSV × 500, todos em respostas não vazias. A estimativa supõe que toda resposta cortada vem vazia; o `proxy.jsonl` não guarda o `doc_id`, então não dá para cruzar chamada a chamada.)

## Conclusão

1. **Não é só truncamento.** No Qwen3.5-9B, o corte no limite de 4096 tokens explica 197 das 640 respostas vazias no GSM8K e 148 das 327 no MATH-500. As outras ~443 (GSM8K) e ~179 (MATH-500) terminaram com `finish_reason=stop` e `content` vazio.
2. **A nota está dominada por resposta vazia, não por erro de raciocínio.** Nas respostas que vieram preenchidas, o Qwen3.5-9B acerta 95,6% (GSM8K) e 93,6% (MATH-500), no nível do que dá com raciocínio desligado (93,4% no GSM8K). Os 49,2% e 32,4% de `raciocinio.csv` medem outra coisa e **não devem entrar no estimador** como "nota com raciocínio" do Qwen3.5-9B.
3. **Hipótese (não verificada).** O llama-server separa o pensamento em `reasoning_content` e deixa o resto em `content`. Se o modelo encerra a geração sem fechar `</think>`, tudo vai para `reasoning_content` e o `content` fica vazio. O Qwen3-8B, no mesmo servidor e na mesma configuração, quase não tem esse problema (36 vazias, quase todas cortadas), então parece específico do template/formato do Qwen3.5. Para confirmar é preciso guardar o JSON bruto da resposta (campo `reasoning_content`) em ~20 questões.
4. **O corte continua importando.** Mesmo sem o problema acima, 15% (GSM8K) e 30% (MATH-500) das respostas do 9B batem em 4096 tokens, com mediana de ~2130 tokens. Um teto de 8192 provavelmente reduziria isso, mas é nova medida e não foi feita.

## Sugestão (não executada)

Repetir só o Qwen3.5-9B com raciocínio ligado depois de (a) gravar a resposta bruta de 20 questões para achar onde o texto some e (b) subir o limite para 8192 tokens, ou então registrar essas linhas como inválidas no resumo. Só diagnóstico, como pedido.
