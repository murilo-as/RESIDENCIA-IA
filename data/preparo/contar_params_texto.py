"""Conta parametros por grupo (texto / visual+audio / mtp) lendo SO o cabecalho dos .safetensors (HTTP Range). Saida: fichas_texto.json"""
import json, os, struct, urllib.request, concurrent.futures as cf, sys
TOKEN = os.environ.get("HF_TOKEN")   # necessario para os repos restritos (gated): HF_TOKEN=hf_xxx python contar_params_texto.py
F = json.load(open("fichas.json"))["fichas"]
NAO_TEXTO = ("visual", "vision", "audio", "multi_modal_projector")
def get(u, h=None, tries=3):
    h = dict(h or {})
    if TOKEN: h["Authorization"] = "Bearer " + TOKEN
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=60).read()
        except Exception as e: err = e
    raise err
def shard(i, fn):
    base = f"https://huggingface.co/{i}/resolve/main/{fn}"
    n = struct.unpack("<Q", get(base, {"Range": "bytes=0-7"}))[0]
    return json.loads(get(base, {"Range": f"bytes=8-{7+n}"}))
def contar(i):
    try: files = sorted(set(json.loads(get(f"https://huggingface.co/{i}/resolve/main/model.safetensors.index.json"))["weight_map"].values()))
    except Exception: files = ["model.safetensors"]
    out = {"texto": 0, "visual_audio": 0, "mtp": 0}
    for fn in files:
        for k, v in shard(i, fn).items():
            if k == "__metadata__": continue
            p = 1
            for d in v["shape"]: p *= d
            g = "mtp" if k.startswith("mtp") else ("visual_audio" if any(s in k for s in NAO_TEXTO) else "texto")
            out[g] += p
    return i, out
alvo = [i for i, f in F.items() if len(f["modalidade"]) > 1 or any("MTP" in a for a in f["avisos"])]
print(len(alvo), "modelos a contar", flush=True)
res = {}
with cf.ThreadPoolExecutor(12) as ex:
    for fut in cf.as_completed([ex.submit(contar, i) for i in alvo]):
        try: i, o = fut.result(); res[i] = o
        except Exception as e: print("ERRO", e, flush=True)
json.dump(res, open("fichas_texto.json", "w"), indent=1)
for i, o in sorted(res.items()):
    tot = F[i]["params"]["total"]; s = sum(o.values())
    print(f"{i:40s} texto {o['texto']/1e9:7.3f} vis/aud {o['visual_audio']/1e9:6.3f} mtp {o['mtp']/1e9:6.3f} soma/api {s/tot:.3f}")
