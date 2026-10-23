# Notas do piloto (DGX Spark, 2026-10-23)

## Versões
- llama.cpp: commit `36e36e63a54fc8f85b95e9c499a022b597e478dd` (build `b1-36e36e6`), 2026-10-23, "hexagon: add CEIL op (#31006)"
- Build: `cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native -DLLAMA_CURL=OFF`
- lm-eval: 0.4.13 (venv `~/piloto/venv`, `--system-site-packages`)
- Ambiente: container `nvcr.io/nvidia/pytorch:26.08-py3` (aarch64), CUDA 13.4, GPU NVIDIA GB10, Python 3.12.3

## Conversão e quantização
```
python llama.cpp/convert_hf_to_gguf.py models/<Modelo> --outtype f16 --outfile models/<modelo>-f16.gguf
llama.cpp/build/bin/llama-quantize models/<modelo>-f16.gguf models/<modelo>-q8_0.gguf Q8_0
llama.cpp/build/bin/llama-quantize models/<modelo>-f16.gguf models/<modelo>-q4_k_m.gguf Q4_K_M
```
Sem matriz de importância (sem calibração). Q8_0 só para o Qwen2.5-7B.

## Modelos (repositórios Hugging Face)
Qwen/Qwen2.5-7B-Instruct, Qwen/Qwen3-8B, Qwen/Qwen3.5-9B (todos convertidos e rodando).

## Tamanhos (bytes)
| Arquivo | Bytes |
|---|---:|
| qwen2.5-7b-instruct-f16 | 15237853888 |
| qwen2.5-7b-instruct-q8_0 | 8098525888 |
| qwen2.5-7b-instruct-q4_k_m | 4683074240 |
| qwen3-8b-f16 | 16388044256 |
| qwen3-8b-q4_k_m | 5027784160 |
| qwen3.5-9b-f16 | 18407321568 |
| qwen3.5-9b-q4_k_m | 5780090848 |

## llama-bench (Qwen2.5-7B, `-ngl 99 -p 512 -n 128`, job 836)
| formato | pp512 (t/s) | tg128 (t/s) |
|---|---:|---:|
| F16 | 3530.31 ± 65.46 | 16.71 ± 0.02 |
| Q8_0 | 3153.77 ± 27.57 | 30.60 ± 0.02 |
| Q4_K_M | 3375.41 ± 44.15 | 47.89 ± 0.02 |

## Teste de geração (llama-cli, Q4_K_M, `-n 128 --single-turn`)
| Modelo | Prompt (t/s) | Geração (t/s) |
|---|---:|---:|
| Qwen2.5-7B | 442.7 | 44.5 |
| Qwen3-8B | 208.9 | 44.3 |
| Qwen3.5-9B | 159.8 | 39.1 |

Qwen3 e Qwen3.5 começam em modo de raciocínio; com `-n 128` a resposta é cortada antes da frase final.

## Ocorrências
- Job 834: download do Qwen3.5-9B falhou com HTTP 429 (limite de taxa do Hugging Face, sem token). Repetido no job 835, converteu sem erro.
- `pip install transformers` atualizou `huggingface_hub` de 1.28.0 para 1.33.0 no venv.
- Job 835 reconverteu o Qwen3-8B (arquivos sobrescritos).
- `~/piloto` ocupa 117 GB; não há backup no cluster.

## MMLU 5-shot, --limit 10 por assunto (job 844)
Mesmo subconjunto nas 3 rodadas (`--limit` pega as 10 primeiras questões de cada um dos 57 assuntos), `--seed 42` (random, numpy, torch e fewshot), `--batch_size 1`, `lm-eval 0.4.13`, transformers 5.20.2, accelerate 1.15.0.
Via llama-server não funcionou: `--model gguf` e `--model local-completions` falham porque o llama-server ignora `echo` e não devolve `logprobs.token_logprobs` (jobs 838 e 839). Os GGUF foram avaliados com `--model hf ... gguf_file=...` (transformers; os pesos do Q4_K_M permanecem quantizados e as contas rodam em float32). Isso NÃO passa pelo motor do llama.cpp.

| Rodada | model_args | mmlu acc | tempo lm-eval (s) | `real` do bash |
|---|---|---:|---:|---|
| bf16 original | `pretrained=models/Qwen2.5-7B-Instruct,dtype=bfloat16` | 0.7649 ± 0.0169 | 989.8 | 16m37 |
| GGUF F16 | `pretrained=models,gguf_file=qwen2.5-7b-instruct-f16.gguf,tokenizer=models/Qwen2.5-7B-Instruct,dtype=float16` | 0.7632 ± 0.0170 | 771.4 | 12m59 |
| GGUF Q4_K_M | `pretrained=models,gguf_file=qwen2.5-7b-instruct-q4_k_m.gguf,tokenizer=models/Qwen2.5-7B-Instruct,dtype=float32` | 0.7632 ± 0.0172 | 958.8 | 16m07 |

O tempo inclui carregar o modelo; não é velocidade de inferência.

Comando (cada rodada; resultados em `~/piloto/resultados/<rodada>/`):
```
WORLD_SIZE=1 RANK=0 LOCAL_RANK=0 MASTER_ADDR=127.0.0.1 MASTER_PORT=29500 \
venv/bin/lm_eval --model hf --model_args "<model_args>" --device cuda \
  --tasks mmlu --num_fewshot 5 --limit 10 --seed 42 --batch_size 1 --output_path resultados/<rodada>
```
Rodado por `03_mmlu/04_mmlu_bf16_vs_gguf.sbatch` (container pytorch, 1 GPU, `HF_HOME=~/piloto/hf_cache`). As variáveis `WORLD_SIZE` etc. são necessárias porque, sob `srun`, o accelerate tenta iniciar torch.distributed e falha sem elas.
Dependências extras instaladas no venv: `lm-eval[api]` (tenacity, tiktoken), `accelerate`, `transformers`, `sentencepiece`, `gguf`, `protobuf`.

## GSM8K via llama-server (job 851)
`llama-server -m models/<gguf> -ngl 99 -np 8 -c 32768 --host 127.0.0.1 --port 8080` (build b1-36e36e6), 5-shot, `--limit 50` (as 50 primeiras questoes), temperatura 0, max_gen_toks 2048, 8 requisicoes em paralelo (`num_concurrent=8`).
Entre o lm-eval e o servidor ha um proxy (`04_gsm8k/proxy.py`, porta 8081) que grava `usage.completion_tokens` e `finish_reason` de cada resposta em `proxy.jsonl`; `04_gsm8k/analisar.py` resume. Scripts: `04_gsm8k/submeter_gsm8k.sbatch` -> `04_gsm8k/rodar_rodada.sh <tag> <gguf> <on|off>`.
Raciocinio desligado: `--chat-template-kwargs '{"enable_thinking":false}'` no llama-server. Com raciocinio ligado o servidor separa o pensamento da resposta; o lm-eval pontua so a resposta final, e os tokens do pensamento entram na contagem.

Comando do lm-eval (cada rodada, resultados e amostras em `resultados_gsm8k/<tag>/`):
```
venv/bin/lm_eval --model local-chat-completions \
  --model_args model=qwen,base_url=http://127.0.0.1:8081/v1/chat/completions,num_concurrent=8,max_retries=1,tokenized_requests=False \
  --tasks gsm8k --limit 50 --apply_chat_template --fewshot_as_multiturn \
  --gen_kwargs temperature=0,max_gen_toks=2048 --log_samples --output_path resultados_gsm8k/<tag>
```

| Rodada | flexible-extract | strict-match | tokens/resposta (media / max) | cortadas em 2048 | tokens/s agregado | janela de geracao | parede do lm_eval |
|---|---:|---:|---|---:|---:|---:|---:|
| Qwen2.5-7B Q4_K_M | 0.80 ± 0.0571 | 0.40 ± 0.0700 | 218.5 / 479 | 0 | 160.3 | 68.1 s | 531.4 s |
| Qwen3-8B Q4_K_M, raciocinio ligado | 0.88 ± 0.0464 | 0.88 ± 0.0464 | 697.3 / 2048 | 1 | 167.9 | 207.6 s | 615.6 s |
| Qwen3-8B Q4_K_M, raciocinio desligado | 0.84 ± 0.0524 | 0.78 ± 0.0592 | 160.5 / 537 | 0 | 135.3 | 59.3 s | 473.9 s |

Notas: tokens/s agregado = total de tokens gerados / janela entre a primeira requisicao e a ultima resposta. A parede do lm_eval e bem maior que a janela de geracao (o resto e carregamento/preparo do lm-eval e do dataset), entao nao serve como medida de vazao. n=50: os erros padrao (~0.05) cobrem as diferencas entre as rodadas de acuracia. A diferenca grande entre strict e flexible no Qwen2.5 vem do formato da resposta (strict exige "#### numero").

## Reorganizacao (2026-10-23)
- Esta pasta passou de `~/piloto` para `~/work/projects/RESIDENCIA-IA/piloto`; os modelos foram para `~/work/models` (sem link simbolico) e os scripts usam esse caminho absoluto.
- Nos diretorios `Qwen3-8B` e `Qwen3.5-9B` foram apagados so os `*.safetensors` (35 GB); ficaram tokenizer, config e demais arquivos pequenos. Para reconverter, baixar de novo do Hugging Face. `Qwen2.5-7B-Instruct` ficou completo (baseline bf16).
- Os comandos acima foram escritos com os caminhos antigos (`models/...`, `~/piloto`); a logica e a mesma, so os caminhos mudaram.
- A build do llama.cpp tem RUNPATH absoluto e deixou de funcionar apos a mudanca; o `build.sbatch` agora apaga `build/` e recompila. O venv teve os caminhos reescritos.
- Scripts renomeados e agrupados por etapa (ver `README.md`). `probe3` e `probe4` (tentativas intermediarias que falharam por falta de `accelerate` e por `WORLD_SIZE`) foram apagados; o que eles ensinaram esta nesta nota e em `03_mmlu/03_teste_rapido_hf_bf16_e_gguf.sbatch`.
