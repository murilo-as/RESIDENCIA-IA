# Ferramenta de decisão de eficiência em LLMs

Recebe a descrição de um problema em texto livre e devolve uma configuração (modelo, técnicas de eficiência e níveis) com justificativa. O escopo é a família Qwen (2.5 em diante), para computadores pessoais. As medições são feitas no DGX Spark. Aplicar a recomendação e verificá-la (etapas 7 e 8) é trabalho manual.

## Pipeline

| # | Etapa | O que faz | Pasta |
|---|---|---|---|
| 1 | Extração | Um LLM (API) transforma o texto do usuário em campos estruturados | `etapa1_extracao/` |
| 2 | Diagnóstico | Transforma o pedido em "o que medir e dentro de quais limites": benchmarks, orçamento de memória, banda, contexto | `etapa2_diagnostico/` |
| 3 | Candidatura | Gera as combinações de modelo + técnicas e descarta as que não cabem | `etapa3_candidatura/` |
| 4 | Estimativa | Estima memória, latência e qualidade de cada candidata; contém as medições que alimentam a qualidade | `etapa4_estimativa/` |
| 5 | Pareto | Elimina candidatas dominadas | `etapa5_pareto/` |
| 6 | Recomendação | Escolhe conforme a preferência e justifica | `etapa6_recomendacao/` |
| 7 | Aplicação | Manual | — |
| 8 | Verificação | Manual | — |

`pipeline.py` roda as etapas 1 a 6 em sequência.

## Estrutura

```
pipeline.py                roda as etapas 1 a 6 em sequência
config.yaml                LLM extrator, limites e pasta de saída
config.py                  lê o config.yaml
data/                      dados compartilhados entre as etapas
etapa1_extracao/
etapa2_diagnostico/
etapa3_candidatura/
etapa4_estimativa/         estimador, análise e medições (medicao/)
piloto/                    testes de ambiente no DGX Spark; o venv dos jobs fica aqui
preparo_dados/             scripts que constroem a base (rodam raramente)
saidas/                    JSON da última execução (fora do git)
```

## Configuração (`config.yaml`)

Toda opção fica em `config.yaml`; os scripts só aceitam o que muda a cada execução. A chave do Gemini fica em `.env` na raiz (`GEMINI_API_KEY=...`); o `config.py` lê o arquivo e uma variável de ambiente com o mesmo nome tem prioridade. O `.env` está no `.gitignore`.

| Chave | Padrão | Para que serve |
|---|---|---|
| `familias` | `[Qwen]` | Famílias do `fichas.json` que entram no pipeline |
| `llm.backend` | `gemini` | LLM que **extrai** o pedido (etapa 1): `gemini`, `openai` (servidor compatível com a API OpenAI: llama-server, Ollama) ou `llamacpp` (.gguf local). Não é o modelo otimizado |
| `llm.modelo` | `gemini-2.5-flash` | Nome do LLM extrator |
| `llm.url` | vazio | Endereço do servidor (só no backend `openai`) |
| `limites.memoria_gb` | vazio | Orçamento de memória; a etapa 3 corta o que não cabe |
| `limites.banda_gb_s` | 89,6 | Banda da máquina simulada, em GB/s (PC médio, DDR5-5600 dual channel, pico teórico, tag C). O decode medido no Spark (273 GB/s) é escalado pela razão das bandas. Vazio = latência só relativa |
| `limites.min_tok_s` | vazio | Meta de tokens/s |
| `saida` | `saidas` | Pasta dos JSON do pipeline |

Vazio = não informado. Os limites do `config.yaml` valem mais que os do texto do pedido. Chave desconhecida no arquivo dá erro.

## Comandos (da raiz do repositório)

| Comando | O que faz |
|---|---|
| `python pipeline.py "texto do pedido"` | Etapas 1 a 4; grava `pedido.json`, `diagnostico.json`, `candidatos.json` e `estimativas.json` na pasta de saída |
| `python pipeline.py --pedido saidas/pedido.json` | Pula a etapa 1 (sem API) |
| `python etapa1_extracao/extrair.py "texto"` | Só a etapa 1; imprime o pedido |
| `python etapa1_extracao/avaliar_extracao.py` | Avalia o LLM do `config.yaml` nos 10 casos; resultado em `resultados/` |
| `python etapa1_extracao/avaliar_extracao.py --gabarito` | Sem LLM: testa só o código (deve dar 120/120) |
| `python etapa2_diagnostico/diagnosticar.py pedido.json [-o diagnostico.json]` | Só a etapa 2 |
| `python etapa3_candidatura/candidatar.py diagnostico.json [-o candidatos.json]` | Só a etapa 3 |
| `python etapa3_candidatura/regras.py` | Valida `fichas.json`, `tecnicas.yaml` e `efeitos.csv` |
| `python etapa4_estimativa/estimar.py candidatos.json diagnostico.json [-o estimativas.json]` | Só a etapa 4 |
| `python etapa4_estimativa/analise.py [-r resultados.csv ...] [-a texto_do_id] [-o analise.md]` | Validação do estimador de qualidade (deixa um modelo de fora e compara) |

Para testar outro orçamento de memória, mude `limites.memoria_gb` ou use `--config outro.yaml`.

## `data/`

| Arquivo | Conteúdo |
|---|---|
| `fichas.json` | Catálogo de 105 fichas: 72 Qwen (no escopo) e 33 Gemma (fora do escopo). Parâmetros, atenção, tokenizer |
| `fichas_eliminadas.json` | 6 fichas Qwen retiradas do escopo: não cabem em 128 GB nem em 4 bits, então não há como medir nem verificar |
| `tecnicas.yaml` | 22 técnicas de eficiência em 4 movimentos (Shrink, Improve, Grow, Speed-up): requisitos, direção esperada do efeito, níveis. Três têm efeito medido (quantização de pesos, quantização do KV, raciocínio ligado/desligado), 12 se aplicam sem medida, 3 exigem treino do zero e 4 são embutidas no modelo |
| `grade.yaml` | Célula tarefa × domínio → benchmarks, medida direta ou indireta, ordem de fallback e especialidade dos modelos (v0.4) |
| `curva_forma_qwen3.csv` | Perda relativa por tamanho do Qwen3 em 4 bits (artigo [arXiv 2505.02214](https://arxiv.org/abs/2505.02214)); só a forma da curva é usada |
| `fichas_kv.py` | Cache de KV teórico por tipo de atenção, a partir de uma ficha |

A `grade.yaml` define:

| Tarefa × domínio | Benchmarks |
|---|---|
| QA × geral | MMLU |
| QA × saúde | MedQA, PubMedQA |
| QA × ciência | GPQA |
| QA × matemática | GSM8K, MATH-500 |
| QA × jurídico | OAB-Exams |
| Código | HumanEval+, MBPP+ |
| Tradução | WMT24++ |

## Etapa 1: Extração

| Arquivo | Para que serve |
|---|---|
| `extrair.py` | Chama o LLM, valida a resposta e liga o nome do modelo ao id do `fichas.json` |
| `pedido.schema.json` | Formato da resposta (campo = valor + trecho do texto que o justifica) |
| `avaliar_extracao.py` | Roda os casos de teste e conta acertos, alucinações, omissões e erros por campo |
| `casos/pedidos.jsonl` | 10 pedidos com gabarito |
| `resultados/` | Saída de cada avaliação (fora do git) |

Tarefas: QA (inclui conversar, resumir, explicar), Código e Tradução. Com o Gemini 2.5 Flash, a avaliação deu 117/120 campos. O filtro de evidência confere que o trecho existe no texto, não que ele sustenta o valor.

## Etapa 2: Diagnóstico

`diagnosticar.py` lê o pedido e a `grade.yaml` e devolve três blocos: **qualidade** (célula, benchmarks, medida direta ou indireta), **memória** (orçamento, contexto alvo, fórmula) e **latência** (banda, escala em relação ao Spark, meta opcional de tokens/s). Não calcula números de opções.

Regras: tarefa vazia vira QA e domínio vazio vira geral; célula sem benchmark usa o mesmo benchmark do domínio geral; em Código e Tradução o domínio é ignorado com aviso; contexto de 4k, ou 32k com entrada longa. Memória: `config.yaml`, depois o pedido, senão desconhecida (ninguém é excluído). Sem limite informado não há limite.

## Etapa 3: Candidatura

Entrada: `diagnostico.json`. Saída: `candidatos.json`. Sem LLM.

| Campo do `candidatos.json` | Conteúdo |
|---|---|
| `regras` | Cada passo com a regra, o arquivo de origem e a tag |
| `modelos` | Por modelo e técnica medida: aplica, talvez ou não |
| `configuracoes` | Modelo + técnicas + níveis, com memória mínima, se cabe, `status` e `talvez_por` |
| `modelos_descartados` | Quem saiu e por quê |
| `tecnicas_nao_medidas` | Direção do efeito, fora do Pareto |

`candidatar.py` faz: 3.1 escolhe modelos · 3.2 aplica técnicas · 3.3 enumera pesos × KV × modo de raciocínio · 3.4 corta o que não cabe na memória · 3.5 marca o que favorece a preferência · 3.6 lista técnicas não medidas. `regras.py` tem os predicados das técnicas (lógica de 3 valores: sim, talvez, não), a memória mínima teórica, o `config_id` e o validador do `efeitos.csv`.

Regras (tag C, exceto a conta de memória, B):
- Modelo citado no pedido: só ele; as técnicas são recomendadas para ele.
- Sem modelo: catálogo filtrado pela especialidade da célula, base só se `treino=true`, e regra de raciocínio (true → híbrido ligado; false → instruct ou híbrido desligado).
- Memória: pesos + KV com folga de 20%; abaixo disso fica "sem folga". "GB" do pedido é tratado como GiB.
- A preferência só marca; nunca exclui.

## Etapa 4: Estimativa

Entrada: `candidatos.json` e `diagnostico.json`. Saída: `estimativas.json`. Sem LLM.

| Eixo | De onde vem | Tag |
|---|---|---|
| Memória | Mínimo teórico da etapa 3 (pesos + KV) | B |
| Latência, teto | banda ÷ bytes lidos por token; um teto só com pesos e outro com pesos + KV no contexto alvo | B |
| Latência, real | Linha do `efeitos.csv` (própria > paper > card), escalada pela razão das bandas | A ou B; escala C |
| Qualidade | `estimar_qualidade.py`: nota por benchmark a partir das medições | A, B ou C |
| Meta de tok/s | Teto só com pesos abaixo da meta = "não"; acima = "talvez"; com medida = "sim" ou "não" | — |

MoE com parâmetros ativos desconhecidos fica sem teto. Não existe `efeitos.csv` ainda, então a latência real fica sem dado.

### Arquivos

| Arquivo | Para que serve |
|---|---|
| `estimar.py` | Memória, tetos de tokens/s, meta e qualidade de cada configuração, com origem e tag em cada número |
| `estimar_qualidade.py` | Estimador de qualidade (abaixo) |
| `analise.py` | Validação por deixar um modelo de fora: erro por benchmark, por interpolação ou extrapolação, contra a linha de base ingênua |
| `medicao/` | Código, dados e relatórios das medições |

### Estimador de qualidade

`nota(modelo, bits, benchmark) = nota em 16 bits × razão da quantização`.

- **Nota em 16 bits:** reta em ln(tamanho) por dois modelos medidos da mesma linha (família, geração, especialidade, base ou pós-treino).
- **Razão da quantização:** vem dos modelos medidos na mesma prova; a forma por tamanho vem do `curva_forma_qwen3.csv`.
- **Cascata de evidência:** 0 medido · 1 curva da linha · 2 irmão, pela razão · 3 irmão, pela nota · 4 ponte entre provas · 5 prior global · 6 prior de modelo não medido. Cada resultado traz o nível, o intervalo e a tag.
- **Validação:** `analise.py` deixa cada modelo de fora e compara com a linha de base ingênua (copiar a nota do medido de tamanho mais próximo na linha).

### `medicao/`

Mede cada modelo em GGUF com llama.cpp nos níveis F16, Q8_0 e Q4_K_M. Provas de múltipla escolha por log-prob passam pelo lm-eval (hf + `gguf_file`, que desquantiza para fp16); provas geradas usam o llama-server com decodificação gulosa. Os jobs rodam por SLURM no DGX Spark.

| Arquivo | Para que serve |
|---|---|
| `medir.py` | Um processo por modelo: gera o GGUF se faltar e grava uma linha por (modelo, nível, prova). Retomável |
| `letra.py` | Múltipla escolha por geração da letra (`mmlu_letra`, `oab_letra`) |
| `codigo.py`, `pontuar_codigo.py` | HumanEval+ e MBPP+: geração pelo servidor; pontuação do evalplus em container isolado |
| `limpar.py` | Apaga os arquivos de um modelo só se todas as medidas pedidas já estão registradas |
| `pareado.py` | Compara dois níveis questão a questão |
| `resumo.py`, `resumo_prioridade.py` | Escrevem `resumo.md` e `resumo_prioridade_N.md` |
| `validar_letra.py` | Compara a geração de letra com o log-prob no Qwen2.5-7B |
| `baixar_modelos.py` | Baixa modelos do Hugging Face, retomável |
| `arquivo/` | Scripts da primeira campanha e dos testes de aceite (`campanha.sh`, `repetir*.sh`, `etapa1*`, `oab_*`, `plano.txt`) e seus CSVs; não são mais chamados |
| `experimentos/` | Um script por bloco (`p0` a `p3`), `comum.sh` e `plano.txt` (a cadeia de jobs) |
| `tasks/` | Tarefas lm-eval próprias: `oab_exams`, `oab_exams_5shot`, `pubmedqa_qiaojin` |

Dados e relatórios:

| Arquivo | Conteúdo |
|---|---|
| `resultados.csv` | 429 linhas: raciocínio desligado, KV padrão |
| `kv.csv` | 63 linhas: KV quantizado, geração de letra, diagnóstico do MMLU. `kv` = 16, 8, 4 ou k4v8 |
| `raciocinio.csv` | 8 linhas: raciocínio ligado, 4096 tokens por resposta |
| `kv_memoria.csv` | Por servidor com KV configurado: KV pela fórmula, memória usada, RSS, `nvidia-smi` |
| `vazao_moe.csv`, `vazao_moe.md` | Teste de vazão dos MoE |
| `resumo.md`, `resumo_prioridade_1/2/3.md` | Relatórios gerados |
| `DIARIO.md`, `plano_medicao.md` | Registro das ações e plano com estimativas de tempo |

O estimador lê `medicao/resultados*.csv`; `kv.csv` e `raciocinio.csv` não entram nessa leitura. Detalhes de uso: [medicao/README.md](etapa4_estimativa/medicao/README.md).

**Modelos medidos:** 23 (15 pós-treino, 8 base) das famílias Qwen2.5, Qwen3, Qwen3.5 e Qwen3.6. **Provas:** MMLU, MedQA, PubMedQA, OAB, GSM8K, MATH-500, HumanEval+, MBPP+, WMT24++. O GPQA não carregou (dataset não encontrado).

## `piloto/`

Testes que validaram o ambiente do DGX Spark: llama.cpp com CUDA, conversão e quantização de modelos Qwen, avaliação com lm-eval. Cada script é um job SLURM; versões e comandos estão em `piloto/NOTAS.md`. A pasta guarda também o `venv` (fora do git) que todos os jobs de medição usam.

## `preparo_dados/`

| Arquivo | Para que serve |
|---|---|
| `contar_params_texto.py` | Lê o cabeçalho dos safetensors no Hugging Face e conta os parâmetros só do texto. Repositórios fechados exigem `HF_TOKEN` |

## Convenções

- **Tags de confiança:** **A** = verificado na fonte ou medido por nós; **B** = fonte ou regra sem checagem independente; **C** = inferência, fonte única ou proxy.
- O LLM só extrai dados do texto. Toda decisão fica em código, com regra e fonte.
- Valor sem medida fica "desconhecido"; nunca se inventa número.

## Histórico

1. **Piloto.** Ambiente do Spark, llama.cpp, conversão para GGUF, primeiros MMLU e GSM8K em Qwen2.5 (`piloto/`).
2. **Etapas 1 a 3.** Extração com 10 casos anotados, diagnóstico com a grade de benchmarks, candidatura com regras de técnicas e memória.
3. **Etapa 4, memória e latência.** Fórmulas de memória e teto de tokens/s; definição do estimador `nota16 × razão`.
4. **Primeira campanha de medição.** Qwen2.5 3B, 7B e 14B em F16, Q8_0 e Q4_K_M, com MMLU e GSM8K.
5. **Benchmarks novos.** MedQA, PubMedQA, OAB, MATH-500, HumanEval+, MBPP+ e WMT24++; o OAB foi refeito com instrução em português e 5-shot.
6. **Medições da etapa 4.** KV quantizado, raciocínio ligado, geração de letra no lugar do log-prob, modelos base e Qwen3, Qwen3.5 e Qwen3.6, MoE.
7. **Escopo.** Gemma saiu; 6 fichas Qwen grandes demais foram eliminadas (72 restantes).
