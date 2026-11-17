"""3.2: teste de vazao de um MoE em q4_k_m (nao roda as ancoras). Uso: moe_vazao.py Qwen3-30B-A3B
Faz: GGUF f16 -> q4_k_m, llama-bench, 20 questoes de GSM8K pelo llama-server e mmlu com 2 questoes por assunto pelo hf (tempo medido). Acrescenta ao vazao_moe.md e a vazao_moe.csv."""
import os, subprocess, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import medir

modelo = sys.argv[1]
m = medir.Medicao(medir.AQUI, "vazao_moe.csv")
s = medir.Sessao(m, modelo, "q4_k_m", False)
md = os.path.join(medir.AQUI, "vazao_moe.md")
rel = [f"\n## {modelo} q4_k_m ({medir.agora()})\n"]


def passo(nome, f):
    try: return f()
    except Exception:
        rel.append(f"- {nome}: FALHOU\n```\n{traceback.format_exc()[-1200:]}\n```")
        m.log_erro(modelo, "q4_k_m", nome, traceback.format_exc()[-1500:])
        return False


try:
    gguf = s.path()
    rel.append(f"- GGUF q4_k_m: {os.path.getsize(gguf) / 1e9:.1f} GB")
    out = subprocess.run([os.path.join(medir.BIN, "llama-bench"), "-m", gguf, "-ngl", "99", "-p", "512", "-n", "128"], capture_output=True, text=True, timeout=1800).stdout
    rel.append("- llama-bench (pp512 e tg128, tokens/s):\n```\n" + out.strip() + "\n```")
except Exception:
    rel.append(f"- GGUF/llama-bench: FALHOU\n```\n{traceback.format_exc()[-1200:]}\n```")
    open(md, "a").write("\n".join(rel) + "\n")
    raise SystemExit(1)
if passo("gsm8k", lambda: medir.rodar_gerativo(m, s, "gsm8k", 20)) is not False:
    l = [r for r in m.linhas() if r["modelo"] == modelo and r["benchmark"] == "gsm8k"]
    if l:
        t, n, tok = float(l[-1]["tempo_s"]), int(l[-1]["n"]), l[-1]["tokens_por_resposta"]
        rel.append(f"- GSM8K {n} questoes pelo llama-server: {t:.0f} s (acc {l[-1]['acuracia']}, {tok} tokens/resposta). Estimativa do GSM8K completo (1319) em q4_k_m: {t * 1319 / n / 3600:.1f} h")
s.fechar_servidor()
if passo("mmlu", lambda: medir.rodar_loglik(m, s, "mmlu", 2)) is not False:
    l = [r for r in m.linhas() if r["modelo"] == modelo and r["benchmark"] == "mmlu"]
    if l:
        t, n = float(l[-1]["tempo_s"]), int(l[-1]["n"])
        rel.append(f"- MMLU {n} questoes pelo hf (2 por assunto, sem contar a carga do modelo): {t:.0f} s. Estimativa do MMLU de 1425 questoes: {t * 1425 / n / 60:.0f} min por nivel")
s.fechar()
rel.append("- Ancoras inteiras (mmlu, medqa, gsm8k, oab, pubmedqa, math500, wmt24, codigo em 3 niveis): usar as estimativas acima e a razao dos tempos do Qwen2.5-7B (ver plano_medicao.md); nao foram rodadas.")
open(md, "a").write("\n".join(rel) + "\n")
print("\n".join(rel))
