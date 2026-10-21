# Ferramenta de decisão de eficiência em LLMs

Recebe a descrição de um problema em texto livre e recomenda um modelo (Qwen 2.5+ ou Gemma 3+) e técnicas de eficiência, com justificativa. Escopo: computadores pessoais; medições no DGX Spark.

**Estado (outubro/2026):** etapas 1, 2 e 3 implementadas; etapa 4 em desenho; nada medido ainda (`efeitos.csv` vazio). Aplicar e verificar a recomendação (etapas 7 e 8) é manual.

- Etapa 1 (Gemini 2.5 Flash, 10 casos anotados, os mesmos usados para ajustar o prompt): 117/120 (97,5%). Os 3 erros: um `treino=false` inferido de "não tenho dados" (a evidência existe no texto mas não sustenta o valor) e dois domínios `outro` vs `geral` sem efeito na etapa 2. Falta testar em casos novos, nunca vistos pelo prompt.
- Etapa 2: roda nos 10 casos; a `grade.yaml` (7 células) é rascunho a conferir.

## Pipeline

| # | Etapa | O que faz | Pasta |
|---|---|---|---|
| 1 | Extração | Um LLM (API) transforma o texto do usuário em campos estruturados | `etapa1_extracao/` |
| 2 | Diagnóstico | Transforma o pedido em "o que medir e dentro de quais limites": benchmarks, orçamento de memória, banda, contexto | `etapa2_diagnostico/` |
| 3 | Candidatura | Gera as combinações possíveis de modelo + técnicas e descarta as inviáveis | `etapa3_candidatura/` |
| 4 | Estimativa | Estima memória, latência e qualidade de cada candidata | `etapa4_estimativa/` *(v0: fórmulas; qualidade só com medidas)* |
| 5 | Pareto | Elimina candidatas dominadas | *(a fazer)* |
| 6 | Recomendação | Ordena conforme a preferência e justifica | *(a fazer)* |
| 7 | Aplicação | Manual | — |
| 8 | Verificação | Manual; a medida volta para `data/efeitos.csv` | — |

## Estrutura

```
pipeline.py                roda as etapas prontas em sequência (cresce a cada etapa fechada)
config.yaml                LLM extrator, limites e pasta de saída
config.py                  lê o config.yaml
data/                      dados compartilhados entre as etapas
etapa1_extracao/
etapa2_diagnostico/
etapa3_candidatura/
etapa4_estimativa/
preparo_dados/             scripts que constroem a base (rodam raramente)
saidas/                    JSON de cada etapa da última execução (não versionar)
```

## Configuração (`config.yaml`) e comandos

Toda opção fica em `config.yaml`, na raiz. Os scripts só aceitam o que muda a cada execução. A chave do Gemini fica em `.env` na raiz (`GEMINI_API_KEY=...`, uma linha, sem aspas obrigatórias); o `config.py` lê o arquivo sozinho e uma variável de ambiente com o mesmo nome tem prioridade. O `.env` precisa estar no `.gitignore`.

| Chave | Padrão | Para que serve |
|---|---|---|
| `llm.backend` | `gemini` | LLM que **extrai** o pedido (etapa 1): `gemini`, `openai` (servidor compatível com a API OpenAI: llama-server, Ollama) ou `llamacpp` (.gguf local). Não é o modelo Qwen/Gemma otimizado |
| `llm.modelo` | `gemini-2.5-flash` | Nome do LLM extrator |
| `llm.url` | vazio | Endereço do servidor (só no backend `openai`) |
| `limites.memoria_gb` | vazio | Orçamento de memória; a etapa 3 corta o que não cabe |
| `limites.banda_gb_s` | 89,6 | Banda da máquina simulada, em GB/s. Padrão = PC médio (DDR5-5600 dual channel, pico teórico, tag C). Tudo é medido no Spark (273 GB/s); para outra banda, o decode escala pela razão entre as duas. Vazio = latência só relativa |
| `limites.min_tok_s` | vazio | Meta de tokens/s |
| `saida` | `saidas` | Pasta dos JSON do pipeline |

Vazio = não informado. Os limites do `config.yaml` valem mais que os do texto do pedido. Chave desconhecida no arquivo dá erro, para um nome errado não passar em silêncio.

### Comandos (da raiz do repositório)

| Comando | O que faz |
|---|---|
| `python pipeline.py "texto do pedido"` | Etapas 1 → 2 → 3 → 4; grava `pedido.json`, `diagnostico.json`, `candidatos.json` e `estimativas.json` na pasta de saída |
| `python pipeline.py --pedido saidas/pedido.json` | Pula a etapa 1 (sem API) |
| `python etapa1_extracao/extrair.py "texto"` | Só a etapa 1; imprime o pedido |
| `python etapa1_extracao/avaliar_extracao.py` | Avalia o LLM do `config.yaml` nos 10 casos; resultado em `resultados/` |
| `python etapa1_extracao/avaliar_extracao.py --gabarito` | Sem LLM: testa só o código (deve dar 120/120) |
| `python etapa2_diagnostico/diagnosticar.py pedido.json [-o diagnostico.json]` | Só a etapa 2 |
| `python etapa3_candidatura/candidatar.py diagnostico.json [-o candidatos.json]` | Só a etapa 3 |
| `python etapa3_candidatura/regras.py` | Valida `fichas.json`, `tecnicas.yaml` e `efeitos.csv` |

Para testar outro orçamento de memória, mude `limites.memoria_gb` no `config.yaml` (ou crie `teste.yaml` e use `--config teste.yaml`).

## `data/`: a base de dados

| Arquivo | Para que serve |
|---|---|
| `fichas.json` | Catálogo de 111 modelos (78 Qwen, 33 Gemma): parâmetros, atenção, tokenizer |
| `tecnicas.yaml` | 22 técnicas de eficiência em 4 movimentos (Shrink, Improve, Grow, Speed-up): requisitos, direção esperada do efeito, níveis |
| `efeitos.csv` | *(a criar)* Efeitos medidos: uma linha por eixo, com origem, fonte e tag de confiança |
| `grade.yaml` | Célula tarefa × domínio → benchmarks, medida direta ou indireta, ordem de fallback e especialidade dos modelos. Rascunho v0.3: 3 tarefas (QA, Código, Tradução), 7 células; QA × jurídico = OAB-Exams (direta, tag C, a verificar) |
| `fichas_kv.py` | Cache de KV teórico por tipo de atenção, a partir de uma ficha (usado na etapa 4) |

## Etapa 1: Extração (`etapa1_extracao/`)

| Arquivo | Para que serve |
|---|---|
| `extrair.py` | Chama o LLM (Gemini, API compatível com OpenAI ou llama.cpp), valida a resposta e liga o nome do modelo ao id do `fichas.json` |
| `pedido.schema.json` | Formato exato da resposta do LLM (campo = valor + trecho do texto que o justifica) |
| `avaliar_extracao.py` | Roda os casos de teste e conta acertos, alucinações, omissões e erros por campo |
| `casos/pedidos.jsonl` | 10 pedidos com o gabarito anotado |
| `resultados/` | Saída de cada avaliação |

Uso (da raiz do repositório; a chave vem do `.env`):
```
python etapa1_extracao/avaliar_extracao.py             # usa o LLM do config.yaml
python etapa1_extracao/avaliar_extracao.py --gabarito  # testa só o código, sem API (deve dar 120/120)
```

Tarefas: QA (inclui conversar, resumir, explicar), Código e Tradução. "Uso geral" foi fundida em QA.
Limite conhecido: o filtro de evidência confere que o trecho existe no texto, não que ele sustenta o valor.

## Etapa 2: Diagnóstico (`etapa2_diagnostico/`)

Não calcula números de opções (isso é a etapa 4). Deixa pronto, por eixo, o que medir e os limites do pedido.

| Arquivo | Para que serve |
|---|---|
| `diagnosticar.py` | Lê o pedido e a `grade.yaml`; devolve três blocos: **qualidade** (célula, benchmarks, medida direta/indireta, referência = o modelo em 16 bits), **memória** (orçamento em GB, contexto alvo, fórmula, o que falta) e **latência** (banda e escala em relação ao Spark, fórmula, meta opcional de tokens/s, o que falta) |

Regras: tarefa vazia vira QA e domínio vazio vira geral; célula sem benchmark cai no mesmo benchmark no domínio geral; em Código e Tradução o domínio é ignorado com aviso; contexto 4k, ou 32k com entrada longa (hipótese, tag C). Memória: `config.yaml`, depois o pedido, senão desconhecida (nenhum modelo é excluído). Banda: `limites.banda_gb_s` do `config.yaml` (padrão 89,6 GB/s, PC médio); o decode medido no Spark (273 GB/s) é escalado pela razão das bandas (tag C), o prefill não. Banda vazia = latência só relativa. Sem limite informado não há limite: o Pareto mostra o compromisso.

```
python etapa2_diagnostico/diagnosticar.py pedido.json      # limites vêm do config.yaml
```

## Etapa 3: Candidatura (`etapa3_candidatura/`)

Entrada: `diagnostico.json`. Saída: `candidatos.json`. Sem LLM, sem medir qualidade/latência (isso é a etapa 4).

| Campo do `candidatos.json` | Conteúdo |
|---|---|
| `regras` | Cada passo com a regra, o arquivo de origem e a tag |
| `modelos` | Por modelo e técnica medida: aplica, talvez ou não, com a regra e o arquivo |
| `configuracoes` | Modelo + técnicas + níveis, com memória mínima, se cabe, `status` e `talvez_por` |
| `modelos_descartados` | Quem saiu e por quê |
| `tecnicas_nao_medidas` | Direção do efeito, fora do Pareto |

| Arquivo | Para que serve |
|---|---|
| `candidatar.py` | 3.1 escolhe modelos · 3.2 aplica técnicas · 3.3 enumera pesos × KV × modo de raciocínio · 3.4 corta o que não cabe na memória · 3.5 marca o que favorece a preferência · 3.6 lista técnicas não medidas |
| `regras.py` | Predicados das técnicas, lógica de 3 valores (sim / talvez / não), memória mínima teórica, `config_id` e validador do `efeitos.csv` |

Regras (todas tag C, exceto a conta de memória, B):
- Modelo citado no pedido: só ele; recomenda-se técnicas para ele (não troca por parente).
- Sem modelo: catálogo filtrado pela especialidade da célula (`grade.yaml`), base só se `treino=true`, e regra de raciocínio (true → híbrido ligado/thinking; false → instruct/híbrido desligado).
- Memória: pesos + KV, com folga de 20%; abaixo disso fica "sem folga"; orçamento desconhecido não exclui ninguém. "GB" do pedido é tratado como GiB.
- Preferência só marca; nunca exclui.

```
python etapa3_candidatura/candidatar.py saidas/diagnostico.json -o saidas/candidatos.json
```

## Etapa 4: Estimativa (`etapa4_estimativa/`)

Entrada: `candidatos.json` e `diagnostico.json`. Saída: `estimativas.json`. Sem LLM. Para cada configuração, o que se calcula e o que se lê:

| Eixo | De onde vem | Tag |
|---|---|---|
| Memória | Mínimo teórico da etapa 3 (pesos + KV); falta o overhead do motor, a medir no Spark | B |
| Latência de decodificação, teto | banda ÷ bytes lidos por token. Dois tetos: só pesos (limite superior verdadeiro) e pesos + KV no contexto alvo | B |
| Latência de decodificação, real | Linha do `efeitos.csv` (própria > paper > card), medida no Spark e escalada pela razão das bandas | A ou B; escala C |
| Qualidade | Linha do `efeitos.csv` por benchmark da célula. Sem linha, fica nulo | A, B ou C |
| Meta de tok/s | Teto só com pesos abaixo da meta = "nao" com certeza; acima = "talvez"; com medida = "sim" ou "nao" | — |

| Arquivo | Para que serve |
|---|---|
| `estimar.py` | Faz as contas acima e grava `estimativas.json` com origem e tag em cada número |

Sem `efeitos.csv`, o arquivo ainda tem memória, tetos de tokens/s e a meta, mas toda qualidade fica "sem dado". MoE com parâmetros ativos desconhecidos fica sem teto. A eficiência η (fração da banda realmente usada) e o prefill só existem depois das medições.

```
python etapa4_estimativa/estimar.py saidas/candidatos.json saidas/diagnostico.json [-o saidas/estimativas.json]
```

## Preparo dos dados (`preparo_dados/`)

| Arquivo | Para que serve |
|---|---|
| `contar_params_texto.py` | Lê o cabeçalho dos safetensors no Hugging Face e conta os parâmetros só do texto. Repositórios fechados exigem `HF_TOKEN` |

## Convenções

- **Tags de confiança:** **A** = verificado na fonte ou medido por nós; **B** = fonte ou regra sem checagem independente; **C** = inferência, fonte única ou proxy.
- O LLM só extrai dados do texto. Toda decisão fica em código, com regra e fonte.
- Valor sem medida fica "desconhecido"; nunca se inventa número.
