"""Baixa modelos do Hugging Face para work/models, com repeticao e espera (429). Retomavel. Uso: baixar_modelos.py Qwen/Qwen2.5-3B-Instruct ...
Usa o HF_TOKEN do ambiente se existir. Para se o espaco livre ficar abaixo de 80 GB ou a pasta de modelos passar de 450 GB."""
import os, shutil, sys, time
from huggingface_hub import snapshot_download

MODELOS = "/beegfs/home/user_muriloalves/work/models"
AQUI = os.path.dirname(os.path.abspath(__file__))


def tamanho_dir(p): return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs if os.path.isfile(os.path.join(d, f)))


if os.path.exists(os.path.join(AQUI, "PARAR")): sys.exit("PARAR existe: nada a fazer")
falhou = False
for repo in sys.argv[1:]:
    destino = os.path.join(MODELOS, repo.split("/")[1])
    livre, usado = shutil.disk_usage(MODELOS).free, tamanho_dir(MODELOS)
    if livre < 80e9 or usado > 450e9:
        msg = f"espaco livre {livre / 1e9:.0f} GB, pasta de modelos {usado / 1e9:.0f} GB: parando"
        open(os.path.join(AQUI, "PARAR"), "w").write(msg + "\n")
        open(os.path.join(AQUI, "erros.log"), "a").write(f"baixar {repo}: {msg}\n")
        sys.exit(msg)
    for tentativa in range(1, 31):
        try:
            print(f"{repo}: tentativa {tentativa}", flush=True)
            snapshot_download(repo, local_dir=destino)
            print(f"{repo}: ok -> {destino}", flush=True)
            break
        except Exception as e:
            print(f"{repo}: {type(e).__name__}: {str(e)[:300]}", flush=True)
            time.sleep(min(120 * tentativa, 900))
    else:
        falhou = True
        open(os.path.join(AQUI, "erros.log"), "a").write(f"baixar {repo}: falhou apos 30 tentativas\n")
sys.exit(1 if falhou else 0)
