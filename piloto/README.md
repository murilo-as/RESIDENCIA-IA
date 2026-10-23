# Piloto de ambiente (DGX Spark)

Testes para validar o ambiente de medição: llama.cpp com CUDA, conversão e quantização de modelos Qwen, e avaliação com o lm-eval. Resultados, versões e comandos exatos estão em [NOTAS.md](NOTAS.md).

Todos os scripts são jobs Slurm (container PyTorch, nós ARM64). Submeta com o caminho completo, por exemplo `sbatch ~/work/projects/RESIDENCIA-IA/piloto/01_ambiente/02_compilar_llama_cpp.sbatch`. Os logs vão para `~/work/projects/logs/`. Os modelos ficam em `~/work/models/`.

## 01_ambiente
| Script | O que faz |
|---|---|
| `01_diagnostico_ambiente.sbatch` | Lista GPU, CUDA, Python, cmake, git, compilador e disco do nó, dentro do container. Não instala nada. |
| `02_compilar_llama_cpp.sbatch` | Clona e compila o llama.cpp com CUDA (refaz `build/` do zero) e confirma os binários e a GPU. |
| `03_instalar_lm_eval.sbatch` | Cria o `venv` (com os pacotes do container) e instala o lm-evaluation-harness, sem rodar benchmark. |

## 02_modelos
| Script | O que faz |
|---|---|
| `01_baixar_converter_qwen25.sbatch` | Baixa o Qwen2.5-7B-Instruct, converte para GGUF F16 e gera Q8_0 e Q4_K_M. |
| `02_baixar_converter_qwen3_e_qwen35.sbatch` | Baixa Qwen3-8B e Qwen3.5-9B e gera F16 e Q4_K_M de cada um; se um falhar, segue para o outro. |
| `03_teste_geracao_qwen25.sbatch` | Faz uma pergunta curta em português ao Qwen2.5 Q4_K_M com o `llama-cli` e mostra os tokens/s. |
| `04_teste_geracao_qwen3_e_llama_bench.sbatch` | Mesma pergunta nos Q4_K_M do Qwen3 e Qwen3.5, e `llama-bench` do Qwen2.5 em F16, Q8_0 e Q4_K_M. |

## 03_mmlu
| Script | O que faz | Resultado |
|---|---|---|
| `01_tentativa_llama_server_tipo_gguf.sbatch` | Testa o lm-eval contra o `llama-server` (curl e `--model gguf`). | Falhou: o servidor não devolve `token_logprobs`. |
| `02_tentativa_llama_server_local_completions.sbatch` | Instala `lm-eval[api]` e repete com `--model local-completions`. | Falhou: `KeyError: token_logprobs`. |
| `03_teste_rapido_hf_bf16_e_gguf.sbatch` | Teste de funcionamento (`--limit 3`) de `--model hf` no bf16 original e no Q4_K_M via `gguf_file`. | Funcionou. |
| `04_mmlu_bf16_vs_gguf.sbatch` | MMLU 5-shot (`--limit 10` por assunto, seed 42) no bf16, GGUF F16 e GGUF Q4_K_M. | Funcionou; ver NOTAS.md. |

## 04_gsm8k
| Arquivo | O que faz |
|---|---|
| `submeter_gsm8k.sbatch` | Submete as 3 rodadas: Qwen2.5-7B Q4_K_M e Qwen3-8B Q4_K_M com raciocínio ligado e desligado. |
| `rodar_rodada.sh` | Uma rodada: sobe o `llama-server` (8 slots) e o proxy, roda o lm-eval e imprime o resumo. Uso: `<tag> <gguf> <on\|off>`. |
| `proxy.py` | Proxy entre o lm-eval e o servidor que grava tokens gerados e `finish_reason` de cada resposta. |
| `analisar.py` | Resume uma rodada: acurácia, tokens por resposta, respostas cortadas e tokens/s agregado. |

## Pastas geradas
`resultados/` e `resultados_gsm8k/` guardam as saídas do lm-eval e do proxy. `venv/`, `llama.cpp/` e `hf_cache/` não vão para o git (ver `.gitignore`).
