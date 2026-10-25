#!/bin/bash
# Descricao: dentro do container, sobe o llama-server (1 slot) com o Qwen2.5-7B Q4_K_M, roda GSM8K e MATH-500 (20 exemplos, lm-eval via proxy) e gera as solucoes de codigo. Nao executa codigo.
set -u
cd /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/piloto
export HF_HOME=$PWD/hf_cache HF_DATASETS_OFFLINE=1
BASE=resultados/t3_gerativo
mkdir -p $BASE
llama.cpp/build/bin/llama-server -m /beegfs/home/user_muriloalves/work/models/qwen2.5-7b-instruct-q4_k_m.gguf -ngl 99 -np 1 -c 8192 --host 127.0.0.1 --port 8080 > $BASE/server.log 2>&1 &
S=$!
for i in $(seq 150); do curl -sf http://127.0.0.1:8080/health >/dev/null && break; sleep 2; done
for T in gsm8k hendrycks_math500; do
  echo "##### $T (20 exemplos, 1 requisicao por vez)"
  OUT=$BASE/$T; rm -rf $OUT; mkdir -p $OUT
  venv/bin/python 04_gsm8k/proxy.py http://127.0.0.1:8080 $OUT/proxy.jsonl 8081 &
  P=$!
  sleep 2
  T0=$(date +%s.%N)
  timeout 2400 venv/bin/lm_eval --model local-chat-completions \
    --model_args model=qwen,base_url=http://127.0.0.1:8081/v1/chat/completions,num_concurrent=1,max_retries=1,tokenized_requests=False \
    --tasks $T --limit 20 --apply_chat_template --fewshot_as_multiturn \
    --gen_kwargs temperature=0,max_gen_toks=2048 --log_samples --output_path $OUT 2>&1 | tr "\r" "\n" | grep -vE "it/s\]|^Using the latest|^Found the latest" | tail -12
  venv/bin/python -c "import sys,time; print(time.time()-float(sys.argv[1]))" $T0 > $OUT/wall.txt
  kill $P; wait $P 2>/dev/null
  venv/bin/python 04_gsm8k/analisar.py $OUT $T
done
echo "##### codigo (HumanEval+ e MBPP+, 20 de cada)"
venv/bin/python 05_compatibilidade/t3_gerar_codigo.py $BASE/codigo_stats.json 2>&1 | tr "\r" "\n" | grep -vE "it/s\]"
kill $S; wait $S 2>/dev/null
