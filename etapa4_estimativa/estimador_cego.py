"""Teste cego do estimador de qualidade: prever -> medir -> comparar, por modelo (sem pedido/caso).
  python estimador_cego.py prever            grava data/estimador_cego/previsoes.csv (faca commit ANTES de medir)
  python estimador_cego.py medir ALVO...     baixa o modelo, mede (medir.py, protocolo da Spark) e apaga f16/HF no fim
  python estimador_cego.py comparar          estimado x medido, dentro/fora da banda
Os resultados ficam em data/estimador_cego/<modelo>/kv.csv: NAO entram em data/medicoes (o estimador leria como 'medido')."""
import csv, json, os, shutil, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
sys.path.insert(0, AQUI); sys.path.insert(0, os.path.join(AQUI, "medicao"))
import estimar_qualidade as E

PASTA = os.path.join(RAIZ, "data", "estimador_cego")
NIVEL, BITS = "q4_k_m", 4
PROVAS = {"gsm8k": "gsm8k", "math500": "math500", "wmt24": "wmt24"}          # chave do estimador -> benchmark do medir.py
ALVOS = {   # nome: (repo HF, classe esperada)
    "Qwen3-4B-Instruct-2507": ("Qwen/Qwen3-4B-Instruct-2507", "interpolacao"),
    "Qwen3-30B-A3B-Instruct-2507": ("Qwen/Qwen3-30B-A3B-Instruct-2507", "interpolacao"),
    "Qwen3.6-27B": ("Qwen/Qwen3.6-27B", "irmao"),
    "Qwen3.6-35B-A3B": ("Qwen/Qwen3.6-35B-A3B", "irmao"),
    "Qwen3-32B": ("Qwen/Qwen3-32B", "extrapolacao"),
}


def fichas_com_extras():
    """Qwen3-32B nao tem ficha em data/fichas.json: monta uma em memoria a partir da do Qwen3-14B (mesma arquitetura, valores do config.json publicado: 64 camadas,
    64 cabecas de atencao, 8 de KV). So tamanho e linha do modelo importam para a estimativa. Contagem de parametros digitada a mao: confira na API do HF."""
    F = E.fichas()
    if "Qwen/Qwen3-32B" not in F:
        f = json.loads(json.dumps(F["Qwen/Qwen3-14B"])); f["id"] = "Qwen/Qwen3-32B"; f["base_de"] = None
        f["params"].update(total=32762123264, texto=32762123264, por_dtype={"BF16": 32762123264}, disco_bytes=65524246528)
        f["arquitetura"].update(camadas=64, camadas_por_tipo={"full_attention": 64}, camadas_proprias={"full_attention": 64}, q_heads=64)
        f["avisos"] = ["ficha montada a mao para o teste cego (nao esta em data/fichas.json)"]
        F["Qwen/Qwen3-32B"] = f
    return F


def prever():
    F = fichas_com_extras(); M = E.ler_medicoes(E.CSVS, F); formas = E.ler_forma(F)
    os.makedirs(PASTA, exist_ok=True)
    arq = os.path.join(PASTA, "previsoes.csv")
    with open(arq, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["modelo", "nivel", "benchmark", "estimado", "meio_pts", "metodo", "classe_esperada"])
        for nome, (hf, cl) in ALVOS.items():
            for b in PROVAS:
                e = E.estimar_total(F, M, hf, b, bits=BITS, formas=formas)
                if e: w.writerow([nome, NIVEL, PROVAS[b], round(e["valor"], 4), round(e["meio"], 2), e["metodo"], cl]); print(nome, b, round(e["valor"] * 100, 1), "+-", round(e["meio"], 1), e["metodo"])
    print("gravado:", arq)


def medir(nomes):
    import medir as md
    for nome in nomes:
        hf = ALVOS[nome][0]; dest = os.path.join(md.MODELOS, nome); pasta = os.path.join(PASTA, nome)
        os.makedirs(pasta, exist_ok=True)
        if not os.path.exists(os.path.join(dest, "config.json")):
            from huggingface_hub import snapshot_download
            snapshot_download(hf, local_dir=dest)
        cmd = [sys.executable, os.path.join(AQUI, "medicao", "medir.py"), "--modelo", nome, "--niveis", NIVEL, "--benchmarks", *PROVAS.values(),
               "--kv", "16", "--saida", "kv.csv", "--dir", pasta, "--paralelo", "8"]
        print(">>>", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)
        for p in (md.gguf(nome, "f16"),):                                   # libera disco: fica so o q4_k_m
            if os.path.exists(p): os.remove(p)
        shutil.rmtree(dest, ignore_errors=True)


def comparar():
    prev = {(r["modelo"], r["benchmark"]): r for r in csv.DictReader(open(os.path.join(PASTA, "previsoes.csv"), encoding="utf-8"))}
    print(f"{'modelo':<30}{'prova':<9}{'classe':<13}{'estimado':>9}{'banda':>7}{'medido':>8}{'erro':>7}  veredito")
    for (nome, b), p in sorted(prev.items()):
        f = os.path.join(PASTA, nome, "kv.csv")
        if not os.path.exists(f): continue
        m = next((r for r in csv.DictReader(open(f, encoding="utf-8")) if r["modelo"] == nome and r["nivel"] == NIVEL and r["benchmark"] == b and r["kv"] == "16"), None)
        if not m: continue
        est, med = float(p["estimado"]) * 100, float(m["acuracia"]) * 100; meio = float(p["meio_pts"])
        print(f"{nome:<30}{b:<9}{p['classe_esperada']:<13}{est:9.1f}{meio:7.1f}{med:8.1f}{med - est:+7.1f}  {'dentro' if abs(med - est) <= meio else 'FORA'}")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "prever": prever()
    elif c == "medir" and len(sys.argv) > 2 and all(x in ALVOS for x in sys.argv[2:]): medir(sys.argv[2:])
    elif c == "comparar": comparar()
    else: sys.exit(__doc__ + "\nalvos: " + ", ".join(ALVOS))
