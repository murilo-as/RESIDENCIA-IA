#!/bin/bash
# Descricao: Sobe o llama-server e testa o lm-eval via curl e --model gguf (e local-completions sem o extra api). Falhou: o servidor nao devolve token_logprobs.
#SBATCH --job-name=piloto-probe
#SBATCH --account=default
#SBATCH --partition=hpc-spark-45
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --gres=gpu:1
#SBATCH --time=00:40:00
#SBATCH --chdir=/beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
#SBATCH -o /beegfs/home/%u/work/projects/logs/%x-%j.out
#SBATCH -e /beegfs/home/%u/work/projects/logs/%x-%j.err

umask 002

srun --container-image=/beegfs/home/user_muriloalves/work/images/pytorch.sqsh \
     --container-name=user_muriloalves-pytorch \
     --container-mounts=/beegfs/home/user_muriloalves:/beegfs/home/user_muriloalves \
     bash -c '
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache
P=8080
llama.cpp/build/bin/llama-server -m /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-f16.gguf -ngl 99 -np 1 -c 8192 --host 127.0.0.1 --port $P > server.log 2>&1 &
S=$!
for i in $(seq 120); do curl -sf http://127.0.0.1:$P/health >/dev/null && break; sleep 2; done
curl -s http://127.0.0.1:$P/health; echo
echo "##### curl /v1/completions echo+logprobs (o que o lm-eval envia)"
curl -s http://127.0.0.1:$P/v1/completions -H "Content-Type: application/json" \
  -d "{\"model\":\"x\",\"prompt\":\"A capital do Brasil é Brasília\",\"max_tokens\":1,\"logprobs\":1,\"echo\":true,\"temperature\":0}" | head -c 1500; echo
echo "##### lm_eval --model local-completions"
timeout 600 venv/bin/lm_eval --model local-completions \
  --model_args model=qwen,base_url=http://127.0.0.1:$P/v1/completions,tokenizer=/beegfs/home/user_muriloalves/work/models/Qwen2.5-7B-Instruct,tokenized_requests=False,num_concurrent=1,max_retries=1 \
  --tasks mmlu_abstract_algebra --num_fewshot 5 --limit 3 2>&1 | tail -25
echo "##### lm_eval --model gguf"
timeout 600 venv/bin/lm_eval --model gguf --model_args base_url=http://127.0.0.1:$P \
  --tasks mmlu_abstract_algebra --num_fewshot 5 --limit 3 2>&1 | tail -25
kill $S
'
