"""Regras que ligam fichas.json e tecnicas.yaml (etapa 3). Predicados em 3 valores: True, False ou None (talvez)."""
import json, os, sys
import yaml

AQUI = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(AQUI, "..", "data")
sys.path.insert(0, DATA)


def _achar(nome, obrigatorio=True):
    """Procura o arquivo aqui, em ./data e em ../data."""
    for d in (AQUI, os.path.join(AQUI, "data"), DATA):
        p = os.path.join(d, nome)
        if os.path.exists(p): return p
    if obrigatorio: raise FileNotFoundError(f"{nome} nao encontrado perto de {AQUI}")
    return None


def carregar(fichas=None, tecnicas=None):
    return json.load(open(fichas or _achar("fichas.json")))["fichas"], yaml.safe_load(open(tecnicas or _achar("tecnicas.yaml")))


# predicados: (ficha, catálogo, **args) -> True | False | None
def _camadas(f):
    return f["arquitetura"]["camadas_proprias"]

def tem_kv_por_token(f, cat):
    c = _camadas(f); return c.get("full_attention", 0) + c.get("sliding_attention", 0) > 0

def tem_atencao_completa(f, cat):
    return _camadas(f).get("full_attention", 0) > 0

def tipo_em(f, cat, valores):
    return f["tipo"] in valores

def _tamanho(f):
    return f["params"].get("texto") or f["params"]["total"]

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


# chave de configuracao
def config_id(modelo, tecnicas, ctx, T):
    """tecnicas: lista de (id, nivel). Valida e devolve a chave canonica da configuracao."""
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


# etapa 3: recursos do usuario, preferencia, memoria
from fichas_kv import kv_gib

# chave do `exige` (tecnicas.yaml) -> chave de `recursos` (entrada do usuario: True / False / None = nao informou)
RECURSOS = {"dados": "dados", "treino": "treino", "gpu_para_aplicar": "gpu"}
# preferencia -> movimentos que a favorecem. NAO exclui as demais tecnicas: a fronteira de Pareto mostra os dois lados.
FAVORECE = {"qualidade": {"Improve", "Grow"}, "footprint": {"Shrink", "Speed-up"}}
MARGEM = 0.20   # HIPOTESE: folga sobre o minimo teorico; sera trocada pelo fator de correcao medido por motor/arquitetura


def _e3(valores):
    """AND em 3 valores."""
    if any(v is False for v in valores): return False
    if any(v is None for v in valores): return None
    return True

def _exige_um(exige, tem):
    if exige == "nao": return True
    if exige == "sim": return tem            # True -> True, False -> False, None -> None
    return True if tem is True else None     # 'talvez': ter o recurso basta; sem ele ou sem saber, so talvez

def avalia_recursos(t, recursos):
    return _e3([_exige_um(v, recursos.get(RECURSOS[k])) for k, v in t["exige"].items()])

def preferencia_da(t, pref):
    if pref is None: return "indiferente"
    return "favorece" if t["movimento"] in FAVORECE[pref] else "nao_favorece"

ATENDE = {True: "atende", False: "não atende", None: "pode não atender"}
NOME_RECURSO = {"dados": "dados", "treino": "treino", "gpu_para_aplicar": "GPU para aplicar"}
TEM = {True: "você tem", False: "você não tem", None: "você não informou se tem"}


def _porque(t, f, cat, recursos):
    """Regra e fonte de cada decisao (justificativa por passo)."""
    p = []
    for q in t["requer_modelo"]:
        nome = q if isinstance(q, str) else next(iter(q))
        p.append(f"o modelo {ATENDE[_chamar(q, f, cat)]} o requisito {nome}")
    if t["aplica_em"] != "modelo_pronto": p.append(f"só se aplica a {t['aplica_em']}")
    for k, v in t["exige"].items():
        if v != "nao": p.append(f"exige {NOME_RECURSO[k]} ({v}); {TEM[recursos.get(RECURSOS[k])]}")
    return p

def candidatar(f, cat, T, recursos=None, preferencia=None):
    """Para um modelo: situacao de cada tecnica aplicavel a modelo pronto. status: True aplica | None talvez | False nao."""
    recursos = recursos or {}; out = []
    for k, t in T["tecnicas"].items():
        if t["aplica_em"] != "modelo_pronto": continue
        m, r = avalia(t, f, cat), avalia_recursos(t, recursos)
        out.append({"tecnica": k, "modelo": m, "recursos": r, "status": _e3([m, r]), "preferencia": preferencia_da(t, preferencia),
                    "medida_na_v1": t["medida_na_v1"], "porque": _porque(t, f, cat, recursos)})
    return out

def memoria_gib(f, ctx, bits_pesos=16, bits_kv=16):
    """Mínimo teórico: pesos de texto + KV. Em MoE, todos os especialistas ficam na memória."""
    n = f["params"].get("texto") or f["params"]["total"]
    return n * bits_pesos / 8 / 2 ** 30 + kv_gib(f, ctx, bytes_kv=bits_kv / 8)

def cabe(minimo, disponivel, margem=MARGEM):
    """False: nem o mínimo cabe | None: cabe sem folga | True: cabe com folga."""
    if minimo > disponivel: return False
    return True if minimo * (1 + margem) <= disponivel else None

# validacao cruzada
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
