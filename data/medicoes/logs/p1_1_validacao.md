# 1.1 Validacao da geracao de letra (Qwen2.5-7B-Instruct f16)

| prova | log-prob | letra | diferenca (pontos) | respostas sem letra | veredito |
|---|---|---|---|---|---|
| mmlu_letra (n=1425) | 0.7572 (n=1425) | 0.7495 | -0.8 | 0 | aceito |
| oab_letra (n=2205) | 0.5347 (n=2205) | 0.5361 | +0.1 | 0 | aceito |

**Resultado: aceito, a geracao de letra pode substituir o log-prob nos experimentos de KV.**
