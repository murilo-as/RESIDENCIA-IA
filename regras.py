"""Regras que ligam fichas.json e tecnicas.yaml (etapa 3). Predicados em 3 valores: True / False / None (= talvez)."""
import json, sys
import yaml


def carregar(fichas="fichas.json", tecnicas="tecnicas.yaml"):
    return json.load(open(fichas))["fichas"], yaml.safe_load(open(tecnicas))


# ---------- predicados: (ficha, catalogo, **args) -> True | False | None ----------
def _camadas(f):
    return f["arquitetura"]["camadas_proprias"]

def tem_kv_por_token(f, cat):
    c = _camadas(f); return c.get("full_attention", 0) + c.get("sliding_attention", 0) > 0

def tem_atencao_completa(f, cat):
    return _camadas(f).get("full_attention", 0) > 0

def tipo_em(f, cat, valores):
    return f["tipo"] in valores

def _tamanho(f):
    return f["params"]["total"]

def _grupo_tipo(f):
    return f["tipo"] == "base"

def existe_rascunho(f, cat):
    return any(o["id"] != f["id"] and o["tokenizer"] == f["tokenizer"] and _tamanho(o) < _tamanho(f)
               and _grupo_tipo(o) == _grupo_tipo(f) for o in cat.values())

def existe_professor(f, cat):
    return any(o["id"] != f["id"] and o["tokenizer"] == f["tokenizer"] and _tamanho(o) > _tamanho(f) for o in cat.values())

PREDICADOS = {p.__name__: p for p in (tem_kv_por_token, tem_atencao_completa, tipo_em, existe_rascunho, existe_professor)}


def _chamar(req, f, cat):
    nome, args = (req, {}) if isinstance(req, str) else next(iter(req.items()))
    if not isinstance(req, str): args = {"valores": args} if isinstance(args, list) else args
    return PREDICADOS[nome](f, cat, **args)


def avalia(tecnica, f, cat):
    """AND em 3 valores sobre tecnica['requer_modelo']; tambem barra por aplica_em."""
    if tecnica["aplica_em"] != "modelo_pronto":
        return False
    r = [_chamar(q, f, cat) for q in tecnica["requer_modelo"]]
    if any(x is False for x in r): return False
    if any(x is None for x in r): return None
    return True


# ---------- chave de configuracao ----------
def config_id(modelo, tecnicas, ctx, T):
    """tecnicas: lista de (id, nivel). Valida e devolve a chave canonica usada no efeitos.csv."""
    tec = T["tecnicas"]; ids = [t for t, _ in tecnicas]
    if len(set(ids)) != len(ids): raise ValueError("tecnica repetida")
    if len(ids) > T["configuracao"]["max_tecnicas"]: raise ValueError("mais tecnicas que o limite")
    for t, n in tecnicas:
        if t not in tec: raise ValueError(f"tecnica desconhecida: {t}")
        v = tec[t]["niveis"]["valores"]
        if v == "a_definir": raise ValueError(f"{t}: nivel ainda nao definido")
        if n not in v: raise ValueError(f"{t}: nivel {n!r} fora de {v}")
        for u in ids:
            if u in tec[t]["conflita_com"]: raise ValueError(f"{t} conflita com {u}")
    corpo = "+".join(f"{t}:{n}" for t, n in sorted(tecnicas)) or "nenhuma"
    return f"{modelo}|{corpo}|ctx={int(ctx)}"


# ---------- validacao cruzada ----------
def validar():
    F, T = carregar(); tec = T["tecnicas"]; erros = []
    for k, t in tec.items():
        for q in t["requer_modelo"]:
            nome = q if isinstance(q, str) else next(iter(q))
            if nome not in PREDICADOS: erros.append(f"{k}: predicado sem codigo: {nome}")
            if nome not in T["predicados"]: erros.append(f"{k}: predicado fora do registro: {nome}")
        for r in t["combina_com"] + t["conflita_com"]:
            if r not in tec: erros.append(f"{k}: referencia inexistente: {r}")
    for i, f in F.items():
        if not f.get("tokenizer"): erros.append(f"{i}: sem tokenizer")
    print("erros:", erros or "nenhum")
    print(f"{'tecnica':26s} {'aplica':>6s} {'nao':>4s} {'talvez':>6s}")
    for k, t in tec.items():
        if t["aplica_em"] != "modelo_pronto": continue
        r = [avalia(t, f, F) for f in F.values()]
        print(f"{k:26s} {r.count(True):6d} {r.count(False):4d} {r.count(None):6d}")
    ok = config_id("Qwen/Qwen3.5-9B", [("quantizacao_pesos", 4), ("quantizacao_kv", 8)], 32768, T)
    print("config_id:", ok)
    for caso in ([("decoding_especulativo", "a_definir"), ("decoding_paralelo", "a_definir")], [("quantizacao_pesos", 7)]):
        try: config_id("x", caso, 1, T)
        except ValueError as e: print("rejeitado:", e)
    return not erros


if __name__ == "__main__":
    sys.exit(0 if validar() else 1)
