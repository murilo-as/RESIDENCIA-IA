# Ferramenta de decisão de eficiência em LLMs

Recebe a descrição de um problema em texto livre e devolve uma configuração (modelo, técnicas de eficiência e níveis) com justificativa. O escopo é a família Qwen (2.5 em diante), para computadores pessoais. As medições-base são feitas no DGX Spark; as verificações, em outras máquinas (hoje uma RTX 4090).

## Pipeline

| # | Etapa | O que faz | Pasta |
|---|---|---|---|
| 1 | Extração | Um LLM (API) transforma o texto do usuário em campos estruturados | `etapa1_extracao/` |
| 2 | Diagnóstico | Transforma o pedido em "o que medir e dentro de quais limites": benchmarks, orçamento de memória, banda, contexto | `etapa2_diagnostico/` |
| 3 | Candidatura | Gera as combinações de modelo + técnicas e descarta as que não cabem | `etapa3_candidatura/` |
| 4 | Estimativa | Estima memória, latência e qualidade de cada candidata | `etapa4_estimativa/` |
| 5 | Pareto | Elimina candidatas dominadas | `etapa5_pareto/` |
| 6 | Recomendação | Escolhe conforme a preferência e justifica | `etapa6_recomendacao/` |
| 7 | Execução | Roda a configuração recomendada numa máquina (hoje, tarefas de código) | `etapa7_executar_verificar/` |
| 8 | Verificação e atualização | Compara o medido com a estimativa e acrescenta o resultado à base que a etapa 4 lê | `etapa7_executar_verificar/` (mesmo script) |

`pipeline.py` roda as etapas 1 a 6. O ciclo se fecha na etapa 8: o que ela grava em `data/medicoes/` é lido pela etapa 4 na próxima execução.

```
texto → 1 extração → 2 diagnóstico → 3 candidatura → 4 estimativa → 5 Pareto → 6 recomendação
                                                          ↑                          │
                                       data/medicoes/ ←── 8 verificação ←── 7 execução ┘
```

## Estrutura do repositório

```
README.md · config.yaml · config.py · pipeline.py · .env (chave do Gemini, fora do git)

etapa1_extracao/ … etapa6_recomendacao/    uma pasta por etapa; o código de cada uma
etapa7_executar_verificar/                 etapas 7 e 8: verificar.py e casos/ (um JSON por modelo a verificar)

data/                                      tudo que as etapas leem
  fichas.json, tecnicas.yaml, grade.yaml, …  catálogo de modelos, técnicas e benchmarks
  medicoes/                                  medidas: resultados.csv, kv.csv, raciocinio.csv, verificacoes.csv, velocidade.csv, …
  preparo/                                   scripts que constroem as fichas (rodam raramente)

casos_teste/                               pedidos de ponta a ponta (c1 a c9), cada um com .json e .yaml
resultados/<modelo>/<data>_<o que foi>/    saída bruta de cada verificação, agrupada por modelo (no git)
docs/<origem>/                             relatórios, diário e planos; nome = AAAA-MM-DD_<origem>_<conteúdo>.md
arquivo/                                   o que não é mais chamado, com período e origem no nome da pasta
saidas/                                    JSON da última execução do pipeline (fora do git)
modelos/                                   GGUF baixados pela verificação (fora do git)
```

Convenção de nomes: documentos levam a data (ou o período) e a origem no nome (`2026-10-31_spark_plano-de-medicao.md`); resultados ficam sob o modelo (`resultados/Qwen2.5-Coder-1.5B-Instruct/2026-11-16_verificacao_q8_0_kv8/`).

## Configuração (`config.yaml`)

Toda opção fica em `config.yaml`; os scripts só aceitam o que muda a cada execução. A chave do Gemini fica em `.env` na raiz (`GEMINI_API_KEY=...`); o `config.py` lê o arquivo e uma variável de ambiente com o mesmo nome tem prioridade. O `.env` está no `.gitignore`.

| Chave | Padrão | Para que serve |
|---|---|---|
| `familias` | `[Qwen]` | Famílias do `fichas.json` que entram no pipeline |
| `llm.backend` | `gemini` | LLM que **extrai** o pedido (etapa 1): `gemini`, `openai` (servidor compatível com a API OpenAI: llama-server, Ollama) ou `llamacpp` (.gguf local). Não é o modelo otimizado |
| `llm.modelo` | `gemini-2.5-flash` | Nome do LLM extrator |
| `llm.url` | vazio | Endereço do servidor (só no backend `openai`) |
| `limites.memoria_gb` | vazio | Orçamento de memória; a etapa 3 corta o que não cabe |
| `limites.banda_gb_s` | 89,6 | Banda da máquina simulada, em GB/s (PC médio, DDR5-5600 dual channel, pico teórico, tag C). Vazio = sem teto de tokens/s |
| `limites.min_tok_s` | vazio | Meta de tokens/s |
| `fontes_medida` | `[spark, verificacao]` | De onde vêm as medidas do estimador: `spark` = `resultados.csv`; `verificacao` = `verificacoes.csv` (etapa 8, outras máquinas). `[spark]` ignora as verificações |
| `limites.folga_memoria` | 0,20 | Folga sobre o mínimo teórico de memória (hipótese); abaixo dela a configuração fica "sem folga" |
| `limites.eficiencia_banda` | 0,45 | Fração da banda usada no decode. Vem de uma medida só (Qwen3.5-35B-A3B Q4_K_M no Spark: 82,4 tok/s contra teto de 182), tag C |
| `saida` | `saidas` | Pasta dos JSON do pipeline |

Vazio = não informado. Os limites do `config.yaml` valem mais que os do texto do pedido. Chave desconhecida no arquivo dá erro.

## Comandos (da raiz do repositório)

| Comando | O que faz |
|---|---|
| `python pipeline.py "texto do pedido"` | Etapas 1 a 6; grava um JSON por etapa na pasta de saída |
| `python pipeline.py --pedido casos_teste/c1_codigo_8gb.json` | Pula a etapa 1 (sem API) |
| `python pipeline.py --pedido casos_teste/c1_codigo_8gb.json --config casos_teste/c1_codigo_8gb.yaml` | Idem, com o orçamento daquele caso |
| `python etapa1_extracao/extrair.py "texto"` | Só a etapa 1; imprime o pedido |
| `python etapa1_extracao/avaliar_extracao.py [--gabarito]` | Avalia o LLM do `config.yaml` nos casos com gabarito (`--gabarito`: sem LLM, testa só o código) |
| `python etapa2_diagnostico/diagnosticar.py pedido.json` | Só a etapa 2 |
| `python etapa3_candidatura/candidatar.py diagnostico.json` | Só a etapa 3 |
| `python etapa3_candidatura/regras.py` | Valida `fichas.json` e `tecnicas.yaml` |
| `python etapa4_estimativa/estimar.py candidatos.json diagnostico.json` | Só a etapa 4 |
| `python etapa4_estimativa/analise.py [-a texto_do_id] [-o analise.md]` | Validação do estimador de qualidade (deixa um modelo de fora e compara) |
| `python etapa7_executar_verificar/verificar.py etapa7_executar_verificar/casos/<caso>.json --llama-dir <build/bin>` | Etapas 7 e 8: roda, compara e acrescenta à base |
| `python etapa7_executar_verificar/verificar.py --so-ingerir <resultado.json> [--dry-run]` | Só acrescenta à base um resultado já medido |

## `data/`

| Arquivo | Conteúdo |
|---|---|
| `fichas.json` | Catálogo de fichas: Qwen (no escopo) e Gemma (fora do escopo). Parâmetros, atenção, tokenizer |
| `fichas_eliminadas.json` | Fichas Qwen retiradas do escopo: não cabem em 128 GB nem em 4 bits, então não há como medir nem verificar |
| `tecnicas.yaml` | 22 técnicas de eficiência em 4 movimentos (Shrink, Improve, Grow, Speed-up): requisitos, direção esperada do efeito, níveis. Três têm efeito medido (quantização de pesos, quantização do KV, raciocínio ligado/desligado), 12 se aplicam sem medida, 3 exigem treino do zero e 4 são embutidas no modelo |
| `grade.yaml` | Célula tarefa × domínio → benchmarks, medida direta ou indireta, ordem de fallback e especialidade dos modelos |
| `curva_forma_qwen3.csv` | Perda relativa por tamanho do Qwen3 em 4 bits (artigo [arXiv 2505.02214](https://arxiv.org/abs/2505.02214)); só a forma da curva é usada |
| `fichas_kv.py` | Cache de KV teórico por tipo de atenção, a partir de uma ficha |
| `preparo/contar_params_texto.py` | Lê o cabeçalho dos safetensors no Hugging Face e conta os parâmetros só do texto. Repositórios fechados exigem `HF_TOKEN` |

A `grade.yaml` define:

| Tarefa × domínio | Benchmarks |
|---|---|
| QA × geral | MMLU |
| QA × saúde | MedQA, PubMedQA |
| QA × ciência | sem célula própria: usa MMLU (indireta) |
| QA × matemática | GSM8K, MATH-500 |
| QA × jurídico | OAB-Exams |
| Código | HumanEval+, MBPP+ |
| Tradução | WMT24++ |

### `data/medicoes/`

| Arquivo | Conteúdo | Quem lê |
|---|---|---|
| `resultados.csv` | Uma linha por (modelo, nível de pesos, prova): raciocínio desligado, KV padrão | estimador |
| `kv.csv` | KV quantizado (`kv` = 16, 8, 4 ou k4v8) e geração de letra | estimador |
| `raciocinio.csv` | Raciocínio ligado, 4096 tokens por resposta | estimador |
| `verificacoes.csv` | Notas verificadas em outras máquinas (etapa 8), com o que foi estimado e a faixa | estimador, se `fontes_medida` inclui `verificacao` |
| `velocidade.csv` | tok/s e eficiência da banda medidos na verificação | ainda nenhum (para calibrar `eficiencia_banda`) |
| `kv_memoria.csv` | Por servidor com KV configurado: KV pela fórmula, memória usada, RSS, `nvidia-smi` | conferência da fórmula |
| `vazao_moe.csv` | Vazão dos MoE | conferência |
| `etapa1.json`, `erros.log`, `logs/` | Estado e registro da campanha de medição | `medir.py` |

Medida de 8 bits de uma verificação vale também como nota de 16 bits na curva de tamanho (regra razão 1); linhas com KV 4 bits ficam de fora; a medida da Spark vence em caso de conflito. **Modelos medidos no Spark:** Qwen2.5, Qwen3, Qwen3.5 e Qwen3.6, em F16, Q8_0 e Q4_K_M. **Provas:** MMLU, MedQA, PubMedQA, OAB, GSM8K, MATH-500, HumanEval+, MBPP+, WMT24++.

## Etapa 1: Extração

| Arquivo | Para que serve |
|---|---|
| `extrair.py` | Chama o LLM, valida a resposta e liga o nome do modelo ao id do `fichas.json` |
| `pedido.schema.json` | Formato da resposta (campo = valor + trecho do texto que o justifica) |
| `avaliar_extracao.py` | Roda os casos de teste e conta acertos, alucinações, omissões e erros por campo |
| `casos/pedidos.jsonl`, `casos/pedidos_dificeis.jsonl` | Pedidos com gabarito |
| `resultados/` | Saída de cada avaliação (fora do git) |

Tarefas: QA (inclui conversar, resumir, explicar), Código e Tradução. Com o Gemini 2.5 Flash, a avaliação deu 117/120 campos. O filtro de evidência confere que o trecho existe no texto, não que ele sustenta o valor.

## Etapa 2: Diagnóstico

`diagnosticar.py` lê o pedido e a `grade.yaml` e devolve três blocos: **qualidade** (célula, benchmarks, medida direta ou indireta), **memória** (orçamento, contexto alvo, fórmula) e **latência** (banda, eficiência da banda, meta opcional de tokens/s). Não calcula números de opções.

Regras: tarefa vazia vira QA e domínio vazio vira geral; célula sem benchmark usa o mesmo benchmark do domínio geral; em Código e Tradução o domínio é ignorado com aviso; contexto de 4k, ou 32k com entrada longa. Memória: `config.yaml`, depois o pedido, senão desconhecida (ninguém é excluído). Sem limite informado não há limite.

## Etapa 3: Candidatura

Entrada: `diagnostico.json`. Saída: `candidatos.json`. Sem LLM.

| Campo do `candidatos.json` | Conteúdo |
|---|---|
| `regras` | Cada passo com a regra e o arquivo de origem |
| `modelos` | Por modelo, as técnicas que aplicam ou talvez (medidas ou não), com a regra de cada decisão. A etapa 6 usa essa lista para sugerir técnicas conforme a preferência |
| `configuracoes` | Modelo + técnicas + níveis, com memória mínima, se cabe, `status` e `talvez_por` |
| `modelos_descartados` | Quem saiu e por quê |

`candidatar.py` faz: 3.1 escolhe modelos · 3.2 aplica técnicas · 3.3 enumera pesos × KV × modo de raciocínio · 3.4 corta o que não cabe na memória · 3.5 marca o que favorece a preferência. `regras.py` tem os predicados das técnicas (lógica de 3 valores: sim, talvez, não), a memória mínima teórica, o `config_id` e o validador cruzado de fichas e técnicas.

Regras (tag C, exceto a conta de memória, B):
- Modelo citado no pedido: só ele; as técnicas são recomendadas para ele.
- Sem modelo: catálogo filtrado pela especialidade da célula, base só se `treino=true`, e regra de raciocínio (true → híbrido ligado; false → instruct ou híbrido desligado).
- Memória: pesos + KV com folga (config.yaml: `limites.folga_memoria`, padrão 20%); abaixo disso fica "sem folga". "GB" do pedido é tratado como GiB.
- A preferência só marca; nunca exclui.

## Etapa 4: Estimativa

Entrada: `candidatos.json` e `diagnostico.json`. Saída: `estimativas.json`. Sem LLM.

| Eixo | De onde vem | Tag |
|---|---|---|
| Memória | Mínimo teórico da etapa 3 (pesos + KV) | C |
| Latência | teto = banda ÷ bytes lidos por token; estimativa = teto com KV × `eficiencia_banda` | C |
| Qualidade | `estimar_qualidade.py`: nota por benchmark a partir das medições | A, B ou C |
| Meta de tok/s | Teto só com pesos abaixo da meta = "não"; estimativa na meta ou acima = "sim"; senão "talvez" | — |

MoE com parâmetros ativos desconhecidos fica sem teto. A eficiência da banda cresce com o tamanho do modelo (0,20 no 0,5B e 0,36 no 1,5B na 4090; 0,45 no Qwen3.5-35B-A3B no Spark); o valor do `config.yaml` é um só.

| Arquivo | Para que serve |
|---|---|
| `estimar.py` | Memória, tetos de tokens/s, meta e qualidade de cada configuração, com origem e tag em cada número |
| `estimar_qualidade.py` | Estimador de qualidade (abaixo) |
| `analise.py` | Validação por deixar um modelo de fora: erro por benchmark, por interpolação ou extrapolação, contra a linha de base ingênua |
| `medicao/` | Ferramentas para medir (abaixo) |

### Estimador de qualidade (`estimar_qualidade.py`)

`nota(modelo, bits, benchmark) = nota em 16 bits × razão da quantização`.

- **Nota em 16 bits:** reta em ln(tamanho) por dois modelos medidos da mesma linha (família, geração, especialidade, base ou pós-treino).
- **Razão da quantização:** vem dos modelos medidos na mesma prova; a forma por tamanho vem do `curva_forma_qwen3.csv`.
- **Cascata de evidência:** 0 medido · 1 curva da linha · 2 irmão, pela razão · 3 irmão, pela nota · 4 ponte entre provas · 5 prior global · 6 prior de modelo não medido. Cada resultado traz o nível, o intervalo e a tag.
- **Validação:** `analise.py` deixa cada modelo de fora e compara com a linha de base ingênua (copiar a nota do medido de tamanho mais próximo na linha).

### `etapa4_estimativa/medicao/` (ferramentas; os dados ficam em `data/medicoes/`)

Mede cada modelo em GGUF com llama.cpp nos níveis F16, Q8_0 e Q4_K_M. Provas de múltipla escolha por log-prob passam pelo lm-eval (hf + `gguf_file`, que desquantiza para fp16); provas geradas usam o llama-server com decodificação gulosa. Os jobs rodam por SLURM no DGX Spark. O `medir.py` procura o `llama.cpp/` e o `venv/` na raiz do repositório (e, se não achar, nas pastas antigas do piloto). Guia de uso: [docs/medicao_spark/2026-10-25_a_2026-11-05_spark_como-medir.md](docs/medicao_spark/2026-10-25_a_2026-11-05_spark_como-medir.md).

| Arquivo | Para que serve |
|---|---|
| `medir.py` | Um processo por modelo: gera o GGUF se faltar e grava uma linha por (modelo, nível, prova). Retomável |
| `letra.py` | Múltipla escolha por geração da letra (`mmlu_letra`, `oab_letra`) |
| `codigo.py`, `pontuar_codigo.py` | HumanEval+ e MBPP+: geração pelo servidor; pontuação do evalplus em container isolado |
| `proxy.py` | Proxy usado nas provas de GSM8K |
| `limpar.py` | Apaga os arquivos de um modelo só se todas as medidas pedidas já estão registradas |
| `pareado.py` | Compara dois níveis questão a questão |
| `resumo.py`, `resumo_prioridade.py` | Escrevem relatórios datados em `docs/medicao_spark/` |
| `baixar_modelos.py` | Baixa modelos do Hugging Face, retomável |
| `tasks/` | Tarefas lm-eval próprias: `oab_exams`, `oab_exams_5shot`, `pubmedqa_qiaojin`, `wmt24pp_en_pt_br` |

## Etapas 5 e 6: Pareto e recomendação

`etapa5_pareto/pareto.py` mantém só as candidatas não dominadas em nota, memória, bytes lidos por token e raciocínio. Duas configurações empatam se a diferença de nota cabe na tolerância: 0,5 ponto no mesmo modelo, e o menor intervalo entre modelos diferentes. Configurações com resultado idêntico viram uma só, com `equivalentes`.

`etapa6_recomendacao/recomendar.py` escolhe na fronteira: qualidade = maior piso (nota − intervalo); entre as que empatam com a melhor, a de menor footprint (soma das posições em memória e em bytes lidos por token). Devolve `porque_escolhida`, a origem da nota (medida, curva, irmão, prior), as alternativas e avisos (configurações excluídas e o motivo).

## Etapas 7 e 8: executar, verificar e atualizar

`etapa7_executar_verificar/verificar.py` pega um caso (`casos/*.json`: modelo, GGUF, nível, KV e o que a pipeline estimou), baixa o GGUF para `modelos/`, mede HumanEval+ e MBPP+ completos (mesmo protocolo do Spark) e a velocidade (llama-bench), compara com a estimativa e acrescenta as linhas a `data/medicoes/verificacoes.csv` e `velocidade.csv`. A saída bruta fica em `resultados/<modelo>/<data>_verificacao_<nível>_kv<kv>/`. Teste rápido (`--limite`) nunca entra na base. Rodar o pipeline de novo já usa as medidas novas.

Requisitos: llama.cpp compilado com CUDA e `pip install huggingface_hub datasets evalplus`. O evalplus executa o código gerado pelo modelo: use ambiente descartável.

| Verificação | Estimado | Medido | Faixa |
|---|---|---|---|
| Coder-0,5B q8, HumanEval+ | 78,5 ± 17,1 | 54,9 | fora |
| Coder-0,5B q8, MBPP+ | 50,1 ± 17,1 | 42,9 | dentro |
| Coder-1,5B q8, HumanEval+ | 71,7 ± 9,2 | 65,9 | dentro |
| Coder-1,5B q8, MBPP+ | 56,0 ± 9,1 | 59,5 | dentro |

## `docs/` e `arquivo/`

- `docs/medicao_spark/`: guia de medição, plano, diário, resumos por prioridade e resumo geral, todos com data no nome.
- `arquivo/2026-10_testes_ambiente_execucao/`: testes que validaram o ambiente do DGX Spark (llama.cpp com CUDA, conversão e quantização, lm-eval). Cada script é um job SLURM; versões e comandos em `NOTAS.md`.
- `arquivo/2026-10_medicao_spark/`: scripts das campanhas (`experimentos/`, `etapa1_legado/`, `fumaca/`) e análises pontuais; não são mais chamados.
- `arquivo/2026-11-09_etapa4_teste_camada2_analise_camada2.py`: teste da camada 2 do estimador (razão da quantização) feito em 09/11/2026.

## Convenções

- **Tags de confiança:** **A** = medido por nós; **B** = fonte ou regra sem checagem independente; **C** = inferência, fonte única ou proxy. Aparecem nos resultados do estimador e nas medidas, não nas regras das etapas.
- O LLM só extrai dados do texto. Toda decisão fica em código, com regra e fonte.
- Valor sem medida fica "desconhecido"; nunca se inventa número.

## Histórico

1. **Ambiente.** Spark, llama.cpp, conversão para GGUF, primeiros MMLU e GSM8K em Qwen2.5 (`arquivo/2026-10_testes_ambiente_execucao/`).
2. **Etapas 1 a 3.** Extração com casos anotados, diagnóstico com a grade de benchmarks, candidatura com regras de técnicas e memória.
3. **Etapa 4.** Fórmulas de memória e teto de tokens/s; estimador `nota16 × razão`; campanhas de medição (benchmarks, KV, raciocínio, modelos base, Qwen3 a 3.6, MoE).
4. **Escopo.** Gemma saiu; fichas Qwen grandes demais foram eliminadas.
5. **Etapas 5 e 6.** Pareto com tolerância por empate; recomendação por piso de qualidade e footprint.
6. **Etapas 7 e 8.** Verificação em outra máquina (RTX 4090) que alimenta a base; `fontes_medida` no `config.yaml`.
