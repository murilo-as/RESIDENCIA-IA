"""Resumo de uma rodada: acuracia (lm-eval) + tokens e vazao (proxy.jsonl)."""
import glob, json, os, sys

d = sys.argv[1]
regs = [json.loads(l) for l in open(os.path.join(d, "proxy.jsonl"))]
ok = [r for r in regs if "completion_tokens" in r]
res = json.load(open(sorted(glob.glob(os.path.join(d, "**", "results_*.json"), recursive=True))[-1]))["results"][sys.argv[2] if len(sys.argv) > 2 else "gsm8k"]
tok = [r["completion_tokens"] for r in ok]
dur = max(r["t1"] for r in ok) - min(r["t0"] for r in ok)
wall = float(open(os.path.join(d, "wall.txt")).read())
for k, v in res.items():
    if k != "alias": print(f"{k}: {v}")
print(f"requisicoes: {len(regs)} (sem usage: {len(regs) - len(ok)})")
print(f"tokens gerados por resposta: media {sum(tok) / len(tok):.1f}  max {max(tok)}  total {sum(tok)}")
print(f"respostas cortadas (finish_reason=length): {sum(r['finish_reason'] == 'length' for r in ok)}")
print(f"tokens/s agregado: {sum(tok) / dur:.1f}  (janela de geracao {dur:.1f} s)")
print(f"segundos por exemplo (janela de geracao / n, vale com 1 requisicao por vez): {dur / len(ok):.2f}")
print(f"tempo de parede do lm_eval: {wall:.1f} s")
