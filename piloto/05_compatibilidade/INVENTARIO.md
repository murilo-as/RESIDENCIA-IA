# Inventário de benchmarks (lm-eval 0.4.13)

Rascunho da Parte 3 do T3. Nada foi baixado: os nomes das tasks, métricas e extração vêm da leitura dos YAML e dos `utils.py` do `lm-eval` instalado no `venv`; "gated" e os tamanhos vêm da API/cartão do Hugging Face (só metadados). **As medições (s/exemplo e tokens/resposta) estão pendentes**, porque exigem baixar datasets e o T3 pede aviso antes.

Legenda de confiança em "n do teste": **V** = lido no cartão do dataset nesta sessão; **M** = de memória/pelo nome, a confirmar ao baixar.

| Benchmark | Task no lm-eval 0.4.13 | Dataset (HF) | Gated | n do teste | Tipo / métrica | Como a resposta é extraída |
|---|---|---|---|---|---|---|
| MMLU | `mmlu` (57 subtasks `mmlu_<assunto>`) | `cais/mmlu` | não | 14042 (V) | log-prob (`multiple_choice`); `acc` | maior log-prob entre as letras A/B/C/D; 5-shot vem do `dev` |
| MedQA | `medqa_4options` | `GBaker/MedQA-USMLE-4-options-hf` | não | 1273 (V: 10178 train, 1272 validation, 1273 test) | log-prob; `acc`, `acc_norm` | maior log-prob entre A/B/C/D |
| PubMedQA | `pubmedqa` | `bigbio/pubmed_qa` (`pubmed_qa_labeled_fold0_source`) | não | 500 (M) | log-prob; `acc` | maior log-prob entre "yes", "no", "maybe" |
| GPQA Diamond | `gpqa_diamond_zeroshot` (log-prob, 0-shot); também `gpqa_diamond_n_shot`, `gpqa_diamond_cot_zeroshot`, `gpqa_diamond_cot_n_shot`, `gpqa_diamond_generative_n_shot` | `Idavidrein/gpqa` (`gpqa_diamond`) | **sim** (`gated: auto`: exige conta com os termos aceitos e `HF_TOKEN`) | 198 (M) | zeroshot/n_shot: log-prob, `acc`, `acc_norm`; generativa: `exact_match` | log-prob: letras A–D. Generativa: regex `(?<=The answer is )(.*)(?=.)` (strict) ou última `(X)` (flexible) |
| GSM8K | `gsm8k` (também `gsm8k_cot`, `gsm8k_cot_llama`, ...) | `openai/gsm8k` (`main`) | não | 1319 (V) | gerativa (`generate_until`); `exact_match` | strict: `#### número`; flexible: último número da resposta; 5-shot, temperatura 0 |
| MATH-500 | `hendrycks_math500` (e `minerva_math500`) | `HuggingFaceH4/MATH-500` | não | 500 (V) | gerativa; `exact_match` (`minerva_math500` também `math_verify`) | `hendrycks_math500`: último `\boxed{...}` da resposta comparado com o da solução (`is_equiv`); `minerva_math500`: 4-shot com "Final Answer: The final answer is ...". O Minerva exige `math_verify`, `sympy` e `antlr4-python3-runtime==4.11` |
| OAB-Exams 1ª fase | **não existe task no lm-eval 0.4.13** (nenhum YAML com "oab") | `eduagarcia/oab_exams` | não | 2210, split único `train` (V). Todas têm 4 alternativas A–D, `nullified` é sempre `False` e **não existe campo que distinga a fase**: são 27 provas de 2010 a 2018 com 80 ou 100 questões objetivas (compatível com a 1ª fase). Nada foi filtrado | a definir (task própria em YAML: múltipla escolha por log-prob, `acc`) | letras A–D (`answerKey`) |
| HumanEval+ | `humaneval_plus` (alternativa canônica: `evalplus`) | `evalplus/humanevalplus` | não | 164 (V) | gerativa; `pass@1` (executa código) | trecho gerado até as paradas `\nclass`, `\ndef`, `\n#`, `\nif`, `\nprint`, completando o `prompt`; roda os testes. Exige `HF_ALLOW_CODE_EVAL=1` e `--confirm_run_unsafe_code` |
| MBPP | `mbpp` (e `mbpp_plus`) | `google-research-datasets/mbpp` (`full`); `mbpp_plus`: `evalplus/mbppplus` | não | `mbpp_plus`: 378 (V); `mbpp` (`full`, split test): 500 (M) | gerativa; `pass@1` (executa código) | gerar até `[DONE]`, 3-shot, depois rodar os `test_list`; mesmas exigências de execução de código |
| WMT24++ | **não existe task no lm-eval 0.4.13** (só `wmt14_*` e `wmt16_*` em `translation/`) | `google/wmt24pp` (uma config por par `en-XX_YY`, ex.: `en-pt_BR`) | não | ~55 pares, cerca de 1000 segmentos cada (M) | tradução; chrF/BLEU (sacrebleu) ou COMET | exigiria task própria; comparar com o `wmt16_*` do lm-eval como molde |

## O que ainda falta (Parte 3)
- Baixar os datasets e medir **20 exemplos de cada**, com o Qwen2.5-7B Q4_K_M: log-prob pelo `hf` (MMLU, MedQA, PubMedQA, GPQA, OAB) e gerativos pelo `llama-server` (GSM8K, MATH-500, HumanEval+, MBPP, WMT24++). Para cada um: segundos por exemplo e tokens por resposta.
- Datasets a baixar (todos abertos exceto o GPQA): `cais/mmlu` (já em cache), `openai/gsm8k` (já em cache), `GBaker/MedQA-USMLE-4-options-hf`, `bigbio/pubmed_qa`, `HuggingFaceH4/MATH-500`, `eduagarcia/oab_exams`, `evalplus/humanevalplus`, `evalplus/mbppplus`, `google/wmt24pp` (uma config), mais `Idavidrein/gpqa` (gated).
- GPQA depende de você: aceitar os termos do dataset no Hugging Face e exportar `HF_TOKEN` no ambiente do job. Eu não leio nem gravo o token.
- Duas tasks precisam ser escritas por nós (OAB-Exams e WMT24++), e as de código só rodam com a execução de código liberada.

## Achados do download (job 875, só datasets abertos; GPQA e WMT24++ ficaram de fora)
| Dataset | Resultado |
|---|---|
| `GBaker/MedQA-USMLE-4-options-hf` | ok: train 10178, validation 1272, test 1273; colunas `sent1`, `sent2`, `ending0`..`ending3`, `label` |
| `bigbio/pubmed_qa` (`pubmed_qa_labeled_fold0_source`) | **falhou**: `RuntimeError: Dataset scripts are no longer supported, but found pubmed_qa.py` (o `datasets` 5.0.1 não aceita datasets com script; não há versão parquet convertida). Alternativa aberta: `qiaojin/PubMedQA` (`pqa_labeled`, 1000 questões, sem split de teste fixo), que exigiria task própria e teria n diferente do `pubmedqa` do lm-eval (500) |
| `HuggingFaceH4/MATH-500` | ok: test 500; colunas `problem`, `solution`, `answer`, `subject`, `level`, `unique_id` |
| `eduagarcia/oab_exams` | ok: train 2210; colunas `id`, `question_number`, `exam_id`, `exam_year`, `question_type`, `nullified`, `question`, `choices`, `answerKey`; `question_type` é a área do direito (None em 925 questões); gabarito: B 590, C 567, D 545, A 508 |
| `evalplus/humanevalplus` | ok: test 164; colunas `task_id`, `prompt`, `canonical_solution`, `entry_point`, `test` |
| `evalplus/mbppplus` | ok: test 378; colunas `task_id`, `code`, `prompt`, `source_file`, `test_imports`, `test_list`, `test` |

O `utils.py` da task `oab_exams` filtra questões anuladas e as que não têm 4 alternativas A–D; como nenhuma se enquadra, o filtro não remove nada (2210 questões).

## Medições com 20 exemplos (Qwen2.5-7B Q4_K_M, jobs 877 e 878)
| Benchmark | Via | s/exemplo | tokens (média / máx) | Cortadas em 2048 | Resultado (n=20) |
|---|---|---:|---|---:|---|
| MMLU (`mmlu_abstract_algebra`, 5-shot) | hf, log-prob | 0,333 | contexto 360,1 / 405 | n/a | acc 0,60 ± 0,112 |
| MedQA (`medqa_4options`) | hf, log-prob | 0,287 | contexto 200,6 / 328 | n/a | acc 0,60 ± 0,112 |
| OAB-Exams (`oab_exams`, task própria, 0-shot) | hf, log-prob | 0,294 | contexto 223,5 / 330 | n/a | acc 0,30 ± 0,105 (conferir o prompt) |
| PubMedQA | — | não medido | — | — | falha de carga (`pubmed_qa.py` é script) |
| GPQA Diamond | — | não medido | — | — | gated; aguarda `HF_TOKEN` |
| GSM8K (5-shot, chat) | llama-server | 5,75 | resposta 237,3 / 490 | 0 | flexible 0,75 ± 0,099, strict 0,30 |
| MATH-500 (`hendrycks_math500`) | llama-server | 11,39 | resposta 507,1 / 1342 | 0 | 0,0: artefato da extração (`$...$`), ver NOTAS.md |
| HumanEval+ | llama-server (geração) | 3,60 | resposta 160,8 / 322 | 0 | pass@1 17/20 = 0,85 (base e base+plus) |
| MBPP+ | llama-server (geração) | 4,12 | resposta 182,7 / 285 | 0 | pass@1 base 18/20 = 0,90; base+plus 15/20 = 0,75 |
| WMT24++ | — | não medido | — | — | só documentado |
