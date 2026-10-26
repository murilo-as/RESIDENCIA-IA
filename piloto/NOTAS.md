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
Via llama-server não funcionou: `--model gguf` e `--model local-completions` falham porque o llama-server ignora `echo` e não devolve `logprobs.token_logprobs` (jobs 838 e 839). Os GGUF foram avaliados com `--model hf ... gguf_file=...` (transformers; CORRECAO apos o T1: com dtype=float16 os pesos do Q4_K_M ficam todos em fp16 na memoria, 14.19 GiB; nao medi o caso float32). Isso NÃO passa pelo motor do llama.cpp.

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

## T1: compatibilidade GGUF Q4_K_M com transformers em float16 (job 871)
Script: `05_compatibilidade/t1_carga_e_mmlu_fp16.py` (via `t1_compatibilidade.sbatch`). Resumo em `05_compatibilidade/resumo.md`.
- Carga (`AutoModelForCausalLM.from_pretrained(..., gguf_file=..., dtype=torch.float16, device_map="cuda")`): `model.dtype` float16; todos os 7615616512 parametros em float16 = 14.185 GiB (cuda memory_allocated 14.186 GiB), contra 4.361 GiB do arquivo GGUF (razao 3.25). Tempo de carga 36.1 s. Ou seja, nesse caminho o Q4_K_M e desquantizado para fp16 e nao poupa memoria. O aviso do transformers diz que os pesos "ficam quantizados", mas a medida mostra o contrario para float16.
- MMLU 5-shot, `--limit 10` (570 questoes), seed 42 nas 4 sementes, batch_size 16, dtype float16, amostras salvas em `resultados/t1_gguf_q4km_fp16_bs16/`: acc 0.7632 ± 0.0172 (humanities 0.8000, other 0.7308, social sciences 0.8083, stem 0.7316). Carga do HFLM 34.1 s; avaliacao (`simple_evaluate`, inclui montar as tarefas) 467.0 s.
- Rodada anterior (float32, batch 1, sem `--log_samples`): acc 0.7632 ± 0.0172 e os mesmos valores por grupo. A acuracia agregada nao mudou; nao da para saber se as mesmas questoes foram acertadas, porque aquela rodada nao salvou amostras. Esta salva, e serve de referencia para comparacoes por questao.
- O tempo total (carga + avaliacao = 501.1 s) e menor que o da rodada anterior (958.8 s, que incluia a carga), mas dtype e batch mudaram juntos; nao da para atribuir o ganho a um deles.

## T2: Qwen3-8B e Qwen3.5-9B Q4_K_M com transformers em float16 (job 872)
Script: `05_compatibilidade/t2_qwen3_qwen35_gguf.py`. Resumo completo em `05_compatibilidade/resumo_t2.md`. MMLU 5-shot `--limit 2` (114 questoes), seed 42, batch 16, amostras em `resultados/t2_<modelo>_fp16_bs16/`.
- Qwen3-8B: carregou; classe `Qwen3ForCausalLM`, `model_type=qwen3`; 8190735360 parametros em fp16 = 15.256 GiB (GGUF 4.682 GiB); carga 73.5 s; MMLU 0.8070 ± 0.0392; HFLM 36.7 s, avaliacao 446.4 s.
- Qwen3.5-9B: carregou; classe `Qwen3_5ForCausalLM`, `model_type=qwen3_5_text` (o repositorio original e multimodal, `Qwen3_5ForConditionalGeneration`); 8953803264 parametros em fp16 = 16.678 GiB (GGUF 5.383 GiB); carga 46.2 s; MMLU 0.7544 ± 0.0392; HFLM 2.4 s (sem explicacao, nao confiavel), avaliacao 423.2 s. Sem `flash-linear-attention` o transformers usa uma implementacao de referencia mais lenta.
- Com 114 questoes (erro padrao ~0.039) as acuracias nao distinguem os modelos.

## T3 partes 1 e 2: custo do MMLU e flash-linear-attention (jobs 873 e 874)
Script: `05_compatibilidade/t3_mmlu_custo.py`; resultados em `resultados/t3_<tag>_lim<N>/tempos.json`. `hf` + `gguf_file`, float16, batch 16, seed 42, MMLU 5-shot. Os tempos separam carga do modelo, montagem das 57 tarefas e avaliacao.

Parte 1, Qwen2.5-7B Q4_K_M:
| --limit | questoes (n) | pedidos loglik | carga | montar tarefas | avaliacao | s/questao (avaliacao) | acc |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 285 | 1140 | 42.0 s | 363.3 s | 50.9 s | 0.1785 | 0.7930 ± 0.0239 |
| 20 | 1140 | 4560 | 40.8 s | 363.7 s | 176.0 s | 0.1544 | 0.7588 ± 0.0122 |
- Custo por questao (inclinacao entre os dois pontos): (176.03 - 50.88) / (1140 - 285) = 0.146 s por questao (4 pedidos de log-prob cada).
- Custo fixo: carga ~41 s + montar tarefas ~363.5 s (6.4 s por assunto, quase igual nos dois limites e independente do --limit) + ~9 s de intercepto da avaliacao = ~414 s. A montagem das tarefas domina (explicacao por assunto REFUTADA, ver "Correcao" na secao T3 parte 3): os logs mostram, para cada assunto, "Using the latest cached version of the dataset since cais/mmlu couldn't be found on the Hugging Face Hub".
- Extrapolacao linear (so dois pontos, aproximada): MMLU inteiro (14042 questoes) ~9 + 14042 x 0.146 = ~2060 s de avaliacao, mais os ~400 s fixos.
- As acuracias de 5 e 20 por assunto sao de subconjuntos diferentes e nao se comparam.

Parte 2, Qwen3.5-9B Q4_K_M, --limit 20 (1140 questoes):
| Rodada | carga | montar tarefas | avaliacao | s/questao | acc |
|---|---:|---:|---:|---:|---:|
| sem flash-linear-attention | 8.9 s | 368.0 s | 391.0 s | 0.343 | 0.7167 ± 0.0131 |
| com flash-linear-attention | 64.3 s | 378.5 s | 462.4 s | 0.406 | 0.7175 ± 0.0131 |
- `pip install --only-binary=:all: flash-linear-attention`: o dry-run mostrou que so instalaria `fla-core-0.6.0` e `flash-linear-attention-0.6.0` (sem tocar no torch); instalou. `torch` continua 2.14.0a0+4fdf77b940.nv26.8.63802676 e `transformers` 5.20.2.
- `pip install --only-binary=:all: causal-conv1d` falhou: `ERROR: Could not find a version that satisfies the requirement causal-conv1d (from versions: none)` / `No matching distribution found for causal-conv1d` (nao ha wheel para esta plataforma; nao insisti, nao compilei).
- Com o pacote instalado o aviso "chunk_gated_delta_rule is falling back to its reference PyTorch implementation" sumiu do log, mas a avaliacao ficou 18% MAIS LENTA (462.4 s contra 391.0 s). Hipotese nao verificada: compilacao/autotune do Triton nas primeiras chamadas (o primeiro lote levou 53 s contra 36 s). Uma segunda rodada com o cache do Triton aquecido diria se isso se confirma. A acuracia e a mesma (1 questao de diferenca).
- Comparacao com o T2: aquele foi com --limit 2 (114 questoes), entao nao e comparavel com estes tempos.

## T3 parte 3 (em andamento): datasets e inventario
Datasets abertos baixados para `hf_cache` (job 875): MedQA 4 opcoes (test 1273), MATH-500 (500), OAB-Exams (2210), HumanEval+ (164), MBPP+ (378). `bigbio/pubmed_qa` falhou ("Dataset scripts are no longer supported"). GPQA (gated) e WMT24++ nao foram baixados. Detalhes e a conferencia do OAB em `05_compatibilidade/INVENTARIO.md`. Medicoes de 20 exemplos ainda pendentes.

### T3 parte 3: medicoes de 20 exemplos (Qwen2.5-7B Q4_K_M; jobs 876, 877, 878, 879)
- Rodada offline (job 876, `--limit 20`, `HF_DATASETS_OFFLINE=1`): montar tarefas 364.0 s (normal: 363.7 s), avaliacao 176.7 s (normal: 176.0 s), acc 0.7588 (igual). **`HF_DATASETS_OFFLINE=1` nao reduziu nada**; a hipotese de que o tempo fixo vinha da consulta ao Hub esta refutada.
- **Correcao sobre o custo fixo do MMLU.** No job 877 (`t3_medir_logprob.py`) o `TaskManager()` foi criado fora da medida e montar `mmlu_abstract_algebra` levou 0.85 s. Mesmo assim o job durou 417 s no total, contra ~62 s somados de carga, montagem e avaliacao das 3 tasks: sobram ~355 s, do tamanho dos ~363 s das rodadas anteriores. A explicacao mais provavel e que o tempo fixo de ~6 min esta em criar o `TaskManager()` (indexar os YAML de todas as tasks do lm-eval no BeeGFS), e nao em carregar o MMLU por assunto. **E uma inferencia por exclusao, nao medida direta**; um teste que cronometre `TaskManager()` sozinho confirmaria.
- Log-prob (`t3_medir_logprob.py`, 20 exemplos, 1 job, batch 16; tokens = tokens do contexto, ja com os exemplos few-shot):
  | task | s/exemplo | tokens contexto (media / max) | acc |
  |---|---:|---|---:|
  | mmlu_abstract_algebra (5-shot) | 0.333 | 360.1 / 405 | 0.60 ± 0.112 |
  | medqa_4options | 0.287 | 200.6 / 328 | 0.60 ± 0.112 |
  | oab_exams (task propria, 0-shot) | 0.294 | 223.5 / 330 | 0.30 ± 0.105 |
  A acuracia do OAB (0.30, o acaso e 0.25) com so 20 exemplos nao permite concluir nada, mas vale conferir o prompt/formato antes de usar essa task.
- Gerativo pelo llama-server (1 requisicao por vez, `max_gen_toks=2048`, temperatura 0, 20 exemplos):
  | task | s/exemplo | tokens/resposta (media / max) | cortadas | tokens/s | resultado |
  |---|---:|---|---:|---:|---|
  | gsm8k (5-shot, chat) | 5.75 | 237.3 / 490 | 0 | 41.3 | flexible 0.75 ± 0.099, strict 0.30 ± 0.105 |
  | hendrycks_math500 (0-shot) | 11.39 | 507.1 / 1342 | 0 | 44.5 | exact_match 0.0 (ARTEFATO, ver abaixo) |
  | HumanEval+ (geracao) | 3.60 | 160.8 / 322 | 0 | - | pass@1 pendente (job de pontuacao) |
  | MBPP+ (geracao) | 4.12 | 182.7 / 285 | 0 | - | pass@1 pendente (job de pontuacao) |
- **MATH-500: 0/20 e artefato da extracao, nao capacidade.** O `process_results` de `hendrycks_math` pega o trecho entre o primeiro e o ultimo `$` da resposta e o compara com o `\boxed{}` da solucao. O Qwen2.5-Instruct responde com raciocinio longo em LaTeX com `\( ... \)` e varios `$`, entao o trecho nunca bate. Essa task foi desenhada para modelos base com resposta curta; `minerva_math500` (4-shot, "Final Answer: The final answer is ...", `math_verify`) seria a candidata, mas exige `math_verify`, `sympy` e `antlr4-python3-runtime==4.11`.
- Codigo: `evalplus` 0.3.1 instalado so em `~/work/tmp_codigo/pkgs` (job 879; o pip avisou de conflito de `protobuf` com pacotes `nvidia-cutlass-dsl` do container, que so afeta essa pasta); dados baixados do GitHub: HumanEval+ v0.1.10 (164 problemas) e MBPP+ v0.2.0 (378). As 20+20 solucoes estao em `~/work/tmp_codigo/samples/`; a pontuacao (`t3_evalplus_pontuar.sbatch`, sem a home) ainda nao foi submetida.
- Pontuacao de codigo (job 880, `t3_evalplus_pontuar.sbatch`, conteiner descartavel so com `~/work/tmp_codigo`): **falhou** nos dois datasets com `AssertionError: Missing problems in samples` (evalplus.evaluate exige amostras para TODOS os problemas, 164 e 378; geramos 20 de cada). O `ls /beegfs/home/user_muriloalves` de dentro do conteiner mostrou so `work` (nao listou `.claude`, `piloto` etc., entao a home nao esta montada), mas o conteudo desse `work` nao foi verificado. Correcao proposta (nao aplicada): completar as amostras restantes com solucao vazia, pontuar tudo e calcular o pass@1 so dos 20 primeiros task_id a partir do json de resultados.
- Pontuacao de codigo corrigida (job 881, evalplus 0.3.1): as amostras restantes foram completadas com solucao vazia e o pass@1 foi calculado so nos 20 task_id gerados de cada um. HumanEval+: base 17/20 = 0.85 e base+plus 17/20 = 0.85 (falham HumanEval/1, /6 e /19). MBPP+: base 18/20 = 0.90 e base+plus 15/20 = 0.75 (falham no base Mbpp/6 e /56; falham so no plus Mbpp/7, /11 e /16). Os pass@1 que o evalplus imprime sobre todos os problemas (0.104 e 0.048/0.040) sao diluidos pelas solucoes vazias e conferem com 17/164, 18/378 e 15/378. Amostra de 20: erro padrao ~0.08-0.10.
- **FALHA DE ISOLAMENTO no job 881.** O `find /beegfs/home/user_muriloalves -maxdepth 3` de dentro do conteiner listou `/beegfs/home/user_muriloalves/.triton/cache/...` com os hashes reais do cache do Triton da sua home: **a home estava visivel dentro do conteiner**, embora so se montasse `~/work/tmp_codigo:/work` (e `ls` sem `-a` na tentativa anterior so mostrou `work`). Provavelmente o pyxis/enroot monta a home por padrao nesta instalacao (nao confirmado; a opcao de desligar nao pode ser testada no login). Portanto o codigo gerado pelo modelo foi executado com a home montada. Verificacao feita depois: nenhum arquivo fora de `~/work/tmp_codigo` foi criado ou alterado desde o inicio do job (varredura de `find -newermt`, excluindo `work/models`, `work/images`, `venv`, `llama.cpp`, `.cache`, `.claude`, `.vscode-server`, `tmp_codigo/pkgs` e `tmp_codigo/cache`); isso nao prova que nada foi lido, nem cobre as pastas excluidas. Correcao aplicada aos scripts, ainda nao testada: `--no-container-mount-home` no `srun` de `t3_evalplus_pontuar.sbatch`, mais o job `t3_verificar_isolamento.sbatch` (sem executar codigo) que mostra o que o conteiner enxerga.

## Limpeza (2026-10-25)
Apagados: `~/work/tmp_codigo` (sandbox do evalplus com pkgs, cache e logs, 1.9 GB; recriavel com `05_compatibilidade/t3_evalplus_preparo.sbatch`, mas as amostras geradas foram perdidas), `~/.triton`, `~/.cache/pip` e `fla`/`fla_core`/`flash_linear_attention` do venv (o Qwen3.5 ficou mais lento com eles). Mantidos: modelos (incluindo o F16 do Qwen3-8B e do Qwen3.5-9B), scripts, resultados e logs dos jobs. Os scripts `t3_evalplus_*.sbatch` e `t3_medir_gerativo.sh` ainda citam `tmp_codigo`, que precisa ser recriado pelo preparo antes de gerar ou pontuar codigo de novo.
- Verificacao do isolamento (job 882, `t3_verificar_isolamento.sbatch`, sem executar codigo, COMPLETED em 1min25): com `--no-container-mount-home` e so `~/work/tmp_codigo:/work` montado, `ls /beegfs/home/user_muriloalves`, `ls -d ~/.triton` e `find /beegfs` deram "No such file or directory"; o unico mount de BeeGFS era `/work`, contendo so os arquivos de tmp_codigo. Confirma que a home so aparecia por montagem automatica do pyxis/enroot e que a opcao a desliga. O log do job estava em `tmp_codigo/isolamento-882.out` e foi apagado na limpeza junto com a pasta. A pontuacao do evalplus (job 881) NAO foi repetida com a opcao; o pass@1 vem da execucao com a home visivel. Para rodar codigo gerado de novo: recriar `tmp_codigo` com `t3_evalplus_preparo.sbatch` e usar `t3_evalplus_pontuar.sbatch` (ja com a opcao).
