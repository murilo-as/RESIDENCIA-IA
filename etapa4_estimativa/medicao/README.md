# Medição da fase A (etapa 4)

MMLU (hf + `gguf_file`, float16, batch 16, 5-shot, 25 questões por assunto = 1425, seed 42) e GSM8K (llama-server com 8 slots + proxy, 5-shot, temperatura 0, 1319 questões, `max_gen_toks` 2048) para Qwen2.5 3B, 7B e 14B em f16, q8_0 e q4_k_m. Resultados em [resultados.csv](resultados.csv) e [resumo.md](resumo.md).

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `medir.py` | Um processo por modelo: gera o GGUF se faltar e grava uma linha por (modelo, nível, benchmark) em `resultados.csv`. Retomável (pula o que já está no CSV); falhas vão para `erros.log`. O GSM8K grava `gsm8k` (flexible-extract, principal) e `gsm8k_strict` |
| `pareado.py` | Compara dois níveis questão a questão: n, acurácias, diferença, quantas só um nível acertou e erro padrão da diferença pareada |
| `resumo.py` | Escreve `resumo.md`: tabela do CSV, `erros.log` e o pareado f16 × q4_k_m de cada modelo |
| `baixar_modelos.py` | Baixa modelos do Hugging Face com repetição e espera (429); retomável |
| `campanha.sh` | A campanha inteira, em sequência: teste rápido (`fumaca/`), 3B, 7B, 14B (MMLU; GSM8K q4_k_m, f16, q8_0) e resumo. Os passos completos só rodam se o teste rápido passar |
| `slurm/rodar.sbatch` | Roda qualquer comando no container PyTorch; GPU, tempo e dependências vão na linha de comando |

Pastas: `amostras/` (respostas por questão, fora do git), `fumaca/` (CSV e amostras do teste rápido com o 3B: MMLU com 2 questões por assunto e GSM8K com 20), `logs/` (`estado.txt`, um log por passo e `servidor/` com os logs do llama-server, fora do git).

## Como rodar

O QOS aceita só 2 jobs na fila e 1 em execução por usuário, então a campanha é um único job:
```
P=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto/venv/bin/python
S=slurm/rodar.sbatch      # a partir de etapa4_estimativa/medicao/
sbatch --job-name=baixar --time=04:00:00 $S $P baixar_modelos.py Qwen/Qwen2.5-3B-Instruct Qwen/Qwen2.5-14B-Instruct
sbatch --job-name=campanha --time=1-10:00:00 --gres=gpu:1 --cpus-per-task=8 --mem=72G --dependency=afterany:<id do baixar> $S bash campanha.sh
```
Um passo avulso, por exemplo só o MMLU do 14B: `sbatch --gres=gpu:1 --cpus-per-task=8 --mem=72G --time=04:00:00 $S $P medir.py --modelo Qwen2.5-14B-Instruct --benchmarks mmlu`. Para retomar depois de uma queda, submeta `campanha.sh` de novo.

## Notas
- `tempo_s` é o tempo do `simple_evaluate` (MMLU) ou do `simple_evaluate` com o servidor já no ar (GSM8K). Não inclui carga do modelo, montagem das tarefas nem conversão do GGUF.
- Espaço livre abaixo de 80 GB: o script cria `PARAR`, registra em `erros.log` e os passos seguintes saem na hora.
- No 3B, o `gsm8k_strict` fica perto de 0 (o modelo não escreve `#### número`); use a flexible.
- O MMLU dos GGUF passa pelo `transformers` (desquantiza para fp16), não pelo motor do llama.cpp; só o GSM8K usa o llama.cpp.
