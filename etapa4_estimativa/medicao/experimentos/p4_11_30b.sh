#!/bin/bash
# Antes do 30B-A3B: apaga de logs/teste5.json so as entradas reprovadas deste modelo (o teste de 5 exemplos falhado fica gravado e faria o medir.py pular a prova), depois roda o bloco dividido.
BLOCO=p4_11_30b_teste; source /beegfs/home/user_muriloalves/work/projects/RESIDENCIA-IA/etapa4_estimativa/medicao/experimentos/comum.sh
$PY - <<'PYEOF' 2>&1 | tee -a $LOG
import json, os
p = "logs/teste5.json"
d = json.load(open(p))
ks = [k for k, v in d.items() if k.startswith("Qwen3-30B-A3B|") and not v.get("ok")]
for k in ks: d.pop(k)
json.dump(d, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
print("teste de 5 exemplos apagado para repetir:", ks)
PYEOF
exec bash experimentos/p4_11_grandes_divididos.sh Qwen3-30B-A3B
