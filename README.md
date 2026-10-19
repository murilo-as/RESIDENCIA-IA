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
| 4 | Estimativa | Estima memória, latência e qualidade de cada candidata | `etapa4_estimativa/` *(a fazer)* |
| 5 | Pareto | Elimina candidatas dominadas | *(a fazer)* |
| 6 | Recomendação | Ordena conforme a preferência e justifica | *(a fazer)* |
| 7 | Aplicação | Manual | — |
| 8 | Verificação | Manual; a medida volta para `data/efeitos.csv` | — |

## Estrutura

```
pipeline.py                roda as etapas prontas em sequência (cresce a cada etapa fechada)
data/                      dados compartilhados entre as etapas
etapa1_extracao/
etapa2_diagnostico/
etapa3_candidatura/
preparo_dados/             scripts que constroem a base (rodam raramente)
saidas/                    JSON de cada etapa da última execução (não versionar)
```

Rodar tudo, da raiz: `python pipeline.py "texto do pedido" --backend gemini --modelo gemini-2.5-flash`.
Sem API, a partir de um pedido já extraído: `python pipeline.py --pedido saidas/pedido.json --memoria-gb 8`.

## `data/`: a base de dados

| Arquivo | Para que serve |
|---|---|
| `fichas.json` | Catálogo de 111 modelos (78 Qwen, 33 Gemma): parâmetros, atenção, tokenizer |
| `tecnicas.yaml` | 22 técnicas de eficiência em 4 movimentos (Shrink, Improve, Grow, Speed-up): requisitos, direção esperada do efeito, níveis |
| `efeitos.csv` | *(a criar)* Efeitos medidos: uma linha por eixo, com origem, fonte e tag de confiança |
| `grade.yaml` | Célula tarefa × domínio → benchmarks, medida direta ou indireta, ordem de fallback e especialidade dos modelos. Rascunho v0.2: 3 tarefas (QA, Código, Tradução), 7 células |
| `fichas_kv.py` | Cache de KV teórico por tipo de atenção, a partir de uma ficha (usado na etapa 4) |

## Etapa 1: Extração (`etapa1_extracao/`)

| Arquivo | Para que serve |
|---|---|
| `extrair.py` | Chama o LLM (Gemini, API compatível com OpenAI ou llama.cpp), valida a resposta e liga o nome do modelo ao id do `fichas.json` |
| `pedido.schema.json` | Formato exato da resposta do LLM (campo = valor + trecho do texto que o justifica) |
| `avaliar_extracao.py` | Roda os casos de teste e conta acertos, alucinações, omissões e erros por campo |
| `casos/pedidos.jsonl` | 10 pedidos com o gabarito anotado |
| `resultados/` | Saída de cada avaliação |

Uso (da raiz do repositório; a chave só em variável de ambiente, nunca em arquivo):
```
export GEMINI_API_KEY=...
python etapa1_extracao/avaliar_extracao.py --backend gemini --modelo gemini-2.5-flash
python etapa1_extracao/avaliar_extracao.py --backend gabarito     # testa só o código, sem API (deve dar 120/120)
```

Tarefas: QA (inclui conversar, resumir, explicar), Código e Tradução. "Uso geral" foi fundida em QA.
Limite conhecido: o filtro de evidência confere que o trecho existe no texto, não que ele sustenta o valor.

## Etapa 2: Diagnóstico (`etapa2_diagnostico/`)

Não calcula números de opções (isso é a etapa 4). Deixa pronto, por eixo, o que medir e os limites do pedido.

| Arquivo | Para que serve |
|---|---|
| `diagnosticar.py` | Lê o pedido e a `grade.yaml`; devolve três blocos: **qualidade** (célula, benchmarks, medida direta/indireta, referência = o modelo em 16 bits, piso opcional), **memória** (orçamento em GB, contexto alvo, fórmula, o que falta) e **latência** (banda, fórmula, meta opcional de tokens/s, o que falta) |

Regras: tarefa vazia vira QA e domínio vazio vira geral; célula sem benchmark cai no mesmo benchmark no domínio geral; em Código e Tradução o domínio é ignorado com aviso; contexto 4k, ou 32k com entrada longa (hipótese, tag C). Memória: linha de comando, depois o pedido, senão desconhecida (nenhum modelo é excluído). Banda: só por `--banda-gb-s`; sem ela a latência fica relativa. Sem limite informado não há limite: o Pareto mostra o compromisso.

```
python etapa2_diagnostico/diagnosticar.py pedido.json --memoria-gb 24 --banda-gb-s 1008 --min-tok-s 20 --max-perda-pct 5
```

## Etapa 3: Candidatura (`etapa3_candidatura/`)

| Arquivo | Para que serve |
|---|---|
| `regras.py` | Filtros (técnica exige recurso? modelo suporta? cabe na memória?), geração das configurações e validador do `efeitos.csv` |

## Preparo dos dados (`preparo_dados/`)

| Arquivo | Para que serve |
|---|---|
| `contar_params_texto.py` | Lê o cabeçalho dos safetensors no Hugging Face e conta os parâmetros só do texto. Repositórios fechados exigem `HF_TOKEN` |

## Convenções

- **Tags de confiança:** **A** = verificado na fonte ou medido por nós; **B** = fonte ou regra sem checagem independente; **C** = inferência, fonte única ou proxy.
- O LLM só extrai dados do texto. Toda decisão fica em código, com regra e fonte.
- Valor sem medida fica "desconhecido"; nunca se inventa número.