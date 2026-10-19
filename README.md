# Ferramenta de decisão de eficiência em LLMs

Recebe a descrição de um problema em texto livre e recomenda um modelo (Qwen 2.5+ ou Gemma 3+) e técnicas de eficiência, com justificativa. 

**Estado (outubro/2026):** etapa 3 implementada; etapa 1 implementada e testada em 10 casos; etapas 2 e 4 em desenho; nada medido ainda (`efeitos.csv` vazio). Aplicar e verificar a recomendação (etapas 7 e 8) é manual.

## Pipeline

| # | Etapa | O que faz | Pasta |
|---|---|---|---|
| 1 | Extração | Um LLM (API) transforma o texto do usuário em campos estruturados | `etapa1_extracao/` |
| 2 | Diagnóstico | Define tipo de problema, benchmarks, memória, banda e gargalo | `etapa2_diagnostico/` *(a fazer)* |
| 3 | Candidatura | Gera as combinações possíveis de modelo + técnicas e descarta as inviáveis | `etapa3_candidatura/` |
| 4 | Estimativa | Estima memória, latência e qualidade de cada candidata | `etapa4_estimativa/` *(a fazer)* |
| 5 | Pareto | Elimina candidatas dominadas | *(a fazer)* |
| 6 | Recomendação | Ordena conforme a preferência e justifica | *(a fazer)* |
| 7 | Aplicação | Manual | — |
| 8 | Verificação | Manual; a medida volta para `data/efeitos.csv` | — |

## Estrutura

```
data/                      dados compartilhados entre as etapas
etapa1_extracao/
etapa3_candidatura/
preparo_dados/             scripts que constroem a base (rodam raramente)
```

## `data/`: a base de dados

| Arquivo | Para que serve |
|---|---|
| `fichas.json` | Catálogo de 111 modelos (78 Qwen, 33 Gemma): parâmetros, atenção, tokenizer |
| `tecnicas.yaml` | 22 técnicas de eficiência em 4 movimentos (Shrink, Improve, Grow, Speed-up): requisitos, direção esperada do efeito, níveis |
| `efeitos.csv` |  Efeitos medidos: uma linha por eixo, com origem, fonte e tag de confiança |
| `grade.yaml`, `hardware.json` | Tarefa × domínio × benchmark; especificações de hardware |

## Etapa 1: Extração (`etapa1_extracao/`)

| Arquivo | Para que serve |
|---|---|
| `extrair.py` | Chama o LLM (Gemini, API compatível com OpenAI ou llama.cpp), valida a resposta e liga o nome do modelo ao id do `fichas.json` |
| `pedido.schema.json` | Formato exato da resposta do LLM (campo = valor + trecho do texto que o justifica) |
| `avaliar_extracao.py` | Roda os casos de teste e conta acertos, alucinações, omissões e erros por campo |
| `casos/pedidos.jsonl` | 10 pedidos com o gabarito anotado |
| `resultados/` | Saída de cada avaliação |

Uso:
```
export GEMINI_API_KEY=...
python etapa1_extracao/avaliar_extracao.py --backend gemini --modelo gemini-2.5-flash-lite
python avaliar_extracao.py --backend gabarito     # testa só o código, sem API
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