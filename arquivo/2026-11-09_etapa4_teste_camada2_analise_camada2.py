"""Testes de 09/11/2026 com as ancoras medidas: (1) camada 2 (razao da quantizacao) em 4 e 8 bits: razao 1, irmao, vizinho, media da classe, media da classe com forma;
(2) camada 1 (nota em 16 bits): reta em ln(tamanho) contra reta no logit. Leave-one-out sobre os modelos medidos; erro em pontos da nota. Uso: python analise_camada2.py"""
import os, sys, math, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estimar_qualidade as q
F = {k: v for k, v in q.fichas().items() if v['familia'] == 'Qwen'}
M = q.ler_medicoes(q.CSVS, F)
formas = q.ler_forma(F)
CL = {'conhecimento': ['mmlu', 'medqa', 'pubmedqa', 'oab'], 'geracao': ['gsm8k', 'math500', 'humaneval_plus', 'mbpp_plus'], 'wmt24': ['wmt24']}
cls = {b: c for c, bs in CL.items() for b in bs}
def r_of(i, bits, b):
    return q.razao_medida(M, i, bits, b)
def forma(i): return q.forma(F[i], formas)
models = sorted({i for (i, bits, b) in M if bits == 4 and (i, 16, b) in M})
print(len(models), 'modelos com razao 4 bits')
RES = {}
for bits in (4, 8):
    print('\n=== nivel', bits, 'bits ===')
    res = {}
    for i in models:
        for b in cls:
            rt = r_of(i, bits, b)
            if rt is None: continue
            n16 = M[(i, 16, b)]['valor']
            others = [j for j in models if j != i and r_of(j, bits, b) is not None]
            ocl = [(j, bb) for j in models if j != i for bb in CL[cls[b]] if r_of(j, bits, bb) is not None]
            preds = {'razao=1': 1.0}
            # irmao (mesma arquitetura, sem usar o proprio)
            sib = [j for j in q.irmaos(F, i) if r_of(j, bits, b) is not None]
            if sib: preds['irmao'] = r_of(sib[0], bits, b)
            # vizinho da mesma linha + forma
            viz = [j for j in others if q.linha(F[j]) == q.linha(F[i])]
            if viz:
                j = min(viz, key=lambda j: abs(math.log(q.tam(F[j]) / q.tam(F[i]))))
                rj = r_of(j, bits, b)
                preds['vizinho'] = 1 - (1 - rj) * forma(i) / forma(j) if bits == 4 else rj
            if ocl:
                preds['media_classe'] = 1 - st.mean(1 - r_of(j, bits, bb) for j, bb in ocl)
                if bits == 4:
                    preds['media_classe+forma'] = 1 - st.mean((1 - r_of(j, bits, bb)) / forma(j) for j, bb in ocl) * forma(i)
            for k, p in preds.items():
                res.setdefault((cls[b], k), []).append((i, b, abs(n16 * (p - rt)) * 100))
    RES[bits] = res
    for c in CL:
        base = {(i, b): e for i, b, e in RES[4].get((c, 'razao=1'), [])}
        print(f'-- {c}: n={len(base)}')
        for k in ['razao=1', 'irmao', 'vizinho', 'media_classe', 'media_classe+forma']:
            L = res.get((c, k))
            if not L: continue
            common = [(e, base[(i, b)]) for i, b, e in L if (i, b) in base]
            print(f'   {k:20s} n={len(L):3d}  erro medio {st.mean(e for _,_,e in L):.2f} pts   (razao=1 nos mesmos itens: {st.mean(x for _, x in common):.2f})')

# teste pareado: media_classe+forma contra razao=1 (4 bits), por classe, com erro padrao da diferenca e bootstrap
print('\n=== teste pareado (4 bits): erro(razao=1) - erro(media_classe+forma); positivo = metodo novo melhor ===')
import random
for c in ['conhecimento', 'geracao']:
    a = {(i, b): e for i, b, e in RES[4].get((c, 'razao=1'), [])}
    d = [a[(i, b)] - e for i, b, e in RES[4].get((c, 'media_classe+forma'), [])]
    se = st.stdev(d) / math.sqrt(len(d))
    print(f'{c}: n={len(d)} diferenca media {st.mean(d):+.2f} pts, EP {se:.2f}, razao {st.mean(d)/se:+.1f} EP;  melhor em {sum(x>0 for x in d)}/{len(d)} itens')


# ---- camada 1: reta em ln(tamanho) contra reta no logit da acuracia (nota em 16 bits, mesma linha, >= 2 outros modelos medidos)
print("\n=== camada 1 (16 bits): reta contra logit; positivo = logit melhor ===")
Mx = {k: v for k, v in M.items() if not (k[0].startswith("Qwen/Qwen3.5-") and k[2] in ("mmlu", "math500"))}
Lg = lambda p: math.log(min(max(p, 1e-3), 1 - 1e-3) / (1 - min(max(p, 1e-3), 1 - 1e-3)))
dd = {}
for (i, bits, b), m in Mx.items():
    if bits != 16 or b not in cls or cls[b] == "wmt24": continue
    pts = [(q.tam(F[j]), v["valor"]) for (j, bt, bb), v in Mx.items() if bt == 16 and bb == b and j != i and q.linha(F[j]) == q.linha(F[i])]
    if len(pts) < 2: continue
    lin = min(max(q.curva(q.tam(F[i]), pts)[0], 0), 1)
    lg = 1 / (1 + math.exp(-q.curva(q.tam(F[i]), [(a, Lg(y)) for a, y in pts])[0]))
    dd.setdefault(cls[b], []).append(abs(lin - m["valor"]) * 100 - abs(lg - m["valor"]) * 100)
for c, v in dd.items():
    print(f"{c}: n={len(v)} reta - logit = {st.mean(v):+.2f} pts, EP {st.stdev(v) / math.sqrt(len(v)):.2f}, logit melhor em {sum(x > 0 for x in v)}/{len(v)}")
