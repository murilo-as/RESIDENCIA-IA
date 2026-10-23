#!/bin/bash
# Descricao: Uma rodada de GSM8K: sobe llama-server (-np 8) e o proxy, roda o lm-eval (local-chat-completions) e imprime o resumo. Uso: <tag> <gguf> <on|off>.
# uso: gsm8k_run.sh <tag> <arquivo.gguf> <on|off>   (roda dentro do container)
set -u
TAG=$1; GGUF=$2; THINK=$3
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache
OUT=resultados_gsm8k/$TAG
rm -rf $OUT; mkdir -p $OUT
EXTRA=()
if [ "$THINK" = off ]; then
  llama.cpp/build/bin/llama-server --help 2>&1 | grep -q -- --chat-template-kwargs || { echo "ERRO: llama-server sem --chat-template-kwargs"; exit 3; }
  EXTRA=(--chat-template-kwargs '{"enable_thinking":false}')
fi
echo "##### $TAG ($GGUF, thinking=$THINK)"
llama.cpp/build/bin/llama-server -m /beegfs/home/user_muriloalves/work/models/$GGUF -ngl 99 -np 8 -c 32768 --host 127.0.0.1 --port 8080 "${EXTRA[@]}" > $OUT/server.log 2>&1 &
S=$!
for i in $(seq 150); do curl -sf http://127.0.0.1:8080/health >/dev/null && break; sleep 2; done
curl -s http://127.0.0.1:8080/health; echo
venv/bin/python 04_gsm8k/proxy.py http://127.0.0.1:8080 $OUT/proxy.jsonl 8081 &
P=$!
sleep 2
T0=$(date +%s.%N)
timeout 3000 venv/bin/lm_eval --model local-chat-completions \
  --model_args model=qwen,base_url=http://127.0.0.1:8081/v1/chat/completions,num_concurrent=8,max_retries=1,tokenized_requests=False \
  --tasks gsm8k --limit 50 --apply_chat_template --fewshot_as_multiturn \
  --gen_kwargs temperature=0,max_gen_toks=2048 --log_samples --output_path $OUT 2>&1 | tr "\r" "\n" | grep -v "it/s\]" | tail -15
venv/bin/python -c "import sys,time; print(time.time()-float(sys.argv[1]))" $T0 > $OUT/wall.txt
kill $P $S; wait 2>/dev/null
venv/bin/python 04_gsm8k/analisar.py $OUT
