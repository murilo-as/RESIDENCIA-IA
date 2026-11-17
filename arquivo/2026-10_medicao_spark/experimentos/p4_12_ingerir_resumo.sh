#!/bin/bash
# Junta a ingestao do codigo pontuado (finalizar.sh) e o resumo da prioridade 4 num so job.
bash finalizar.sh
bash experimentos/resumo_prioridade.sh 4
exit 0
