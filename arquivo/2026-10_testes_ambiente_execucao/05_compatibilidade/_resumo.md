# T1: GGUF Q4_K_M com transformers em float16

Script: `t1_carga_e_mmlu_fp16.py`, submetido por `t1_compatibilidade.sbatch` (job 871, 9min57). Qwen2.5-7B-Instruct Q4_K_M, `gguf_file`, `dtype=float16`.

## 1. Carga e memória
| Medida | Valor |
|---|---:|
| `model.dtype` | float16 (todos os parâmetros) |
| Parâmetros | 7.615.616.512 |
| Soma dos bytes dos parâmetros | 14,185 GiB |
| Memória alocada na GPU | 14,186 GiB |
| Arquivo GGUF | 4,361 GiB (4.683.074.240 bytes) |
| Razão parâmetros / GGUF | 3,25 |
| Tempo de carregamento | 36,1 s |

Com `dtype=float16` o transformers desquantiza o Q4_K_M para fp16: a memória é a do modelo em 16 bits, não a do arquivo de 4 bits. O aviso do transformers ("the weights stay quantized regardless") não vale para este caso. O caso `float32` não foi medido.

## 2. MMLU 5-shot, `--limit 10` (570 questões), seed 42, batch 16, float16
| Grupo | acc |
|---|---:|
| mmlu | 0,7632 ± 0,0172 |
| humanities | 0,8000 |
| other | 0,7308 |
| social sciences | 0,8083 |
| stem | 0,7316 |

Carregamento (HFLM): 34,1 s. Avaliação (`simple_evaluate`, inclui montar as tarefas): 467,0 s. Amostras salvas em `../resultados/t1_gguf_q4km_fp16_bs16/` (57 assuntos × 10).

## 3. Comparação com a rodada anterior (float32, batch 1: 0,7632)
A acurácia agregada e a dos quatro grupos são iguais às da rodada anterior, até a quarta casa. Isso não prova que as mesmas questões foram acertadas: aquela rodada não usou `--log_samples`, então não dá para contar quantas questões mudaram. Esta rodada salva as amostras e passa a ser a referência para comparações por questão.
O tempo (carga + avaliação = 501,1 s contra 958,8 s antes, que já incluía a carga) mudou junto com o dtype e o batch; não dá para atribuir o ganho a um deles.
