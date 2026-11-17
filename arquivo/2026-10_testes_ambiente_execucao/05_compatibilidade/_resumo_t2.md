# T2: GGUF Q4_K_M do Qwen3-8B e do Qwen3.5-9B com transformers em float16

Script: `t2_qwen3_qwen35_gguf.py`, submetido por `t2_compatibilidade.sbatch` (job 872, 18min53). Cada modelo em um processo separado. Carga: `from_pretrained(gguf_file=..., dtype=float16)`; MMLU 5-shot `--limit 2` (114 questões), seed 42, `log_samples`, batch 16.

| | Qwen3-8B Q4_K_M | Qwen3.5-9B Q4_K_M |
|---|---|---|
| Carregou | sim | sim |
| Classe reconhecida | `Qwen3ForCausalLM` | `Qwen3_5ForCausalLM` |
| `config.model_type` | `qwen3` | `qwen3_5_text` |
| `config.architectures` | `None` | `['Qwen3_5ForCausalLM']` |
| Parâmetros (todos float16) | 8.190.735.360 | 8.953.803.264 |
| GiB dos parâmetros | 15,256 | 16,678 |
| Arquivo GGUF (GiB) | 4,682 | 5,383 |
| Tempo de carga (parte 1) | 73,5 s | 46,2 s |
| MMLU acc (`--limit 2`) | 0,8070 ± 0,0392 | 0,7544 ± 0,0392 |
| Carregamento HFLM | 36,7 s | 2,4 s |
| Avaliação (`simple_evaluate`) | 446,4 s | 423,2 s |

Observações
- Nos dois casos o Q4_K_M é desquantizado para fp16 na memória (3,3 e 3,1 vezes o arquivo).
- O Qwen3.5-9B, que no Hugging Face é multimodal (`Qwen3_5ForConditionalGeneration`), foi carregado como modelo só de texto (`Qwen3_5ForCausalLM`).
- O transformers avisou que o Qwen3.5 usa uma implementação de referência em PyTorch para `chunk_gated_delta_rule` (falta o pacote `flash-linear-attention`): correto, porém mais lento. Tempos de avaliação do Qwen3.5 não valem como medida de velocidade.
- Com 114 questões o erro padrão é ±0,039: a diferença entre os dois modelos (0,053) não é significativa. Servem só para mostrar que o caminho roda.
- O tempo de carregamento do HFLM do Qwen3.5 (2,4 s) é muito menor que o da parte 1 (46,2 s) e não tenho explicação; trate-o como não confiável. O tempo da parte 1 do Qwen3-8B também inclui leitura fria do arquivo.
- Resultados e amostras: `../resultados/t2_<modelo>_fp16_bs16/`.
