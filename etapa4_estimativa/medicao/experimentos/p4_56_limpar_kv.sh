#!/bin/bash
# Junta p4_5_limpar.sh e p4_6_kv_q4_pequenos.sh num so job (evita uma espera na fila). Cada um e um processo bash separado.
bash experimentos/p4_5_limpar.sh
bash experimentos/p4_6_kv_q4_pequenos.sh
exit 0
