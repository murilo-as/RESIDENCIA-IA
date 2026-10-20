"""Lê o config.yaml e completa com os padrões."""
import os
import yaml


def carregar_env():
    """Lê o .env da raiz e põe CHAVE=valor em os.environ (variável já existente vence)."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(aqui, ".env"), os.path.join(aqui, "..", ".env")):
        if not os.path.exists(p): continue
        for linha in open(p, encoding="utf-8"):
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha: continue
            k, _, v = linha.partition("=")
            k, v = k.removeprefix("export ").strip(), v.strip().strip("'\"")
            if k and k not in os.environ: os.environ[k] = v
        return p


carregar_env()

PADRAO = {"llm": {"backend": "gemini", "modelo": "gemini-2.5-flash", "url": None},
          "limites": {"memoria_gb": None, "banda_gb_s": 89.6, "min_tok_s": None},
          "saida": "saidas"}


def carregar(caminho=None, aqui=None):
    """--config, ou config.yaml na pasta do script / acima."""
    aqui = aqui or os.getcwd()
    if caminho is None:
        for p in (os.path.join(aqui, "config.yaml"), os.path.join(aqui, "..", "config.yaml")):
            if os.path.exists(p): caminho = p; break
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PADRAO.items()}
    if caminho:
        lido = yaml.safe_load(open(caminho)) or {}
        for k, v in lido.items():
            if k not in PADRAO: raise KeyError(f"{caminho}: chave desconhecida {k!r} (validas: {list(PADRAO)})")
            if isinstance(PADRAO[k], dict):
                extra = set(v or {}) - set(PADRAO[k])
                if extra: raise KeyError(f"{caminho}: {k}: chave desconhecida {sorted(extra)} (validas: {list(PADRAO[k])})")
                cfg[k].update(v or {})
            else: cfg[k] = v
        cfg["_arquivo"] = os.path.abspath(caminho)
    return cfg
