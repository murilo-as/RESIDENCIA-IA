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


# chave de configuracao
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


# etapa 3: recursos do usuario, preferencia, memoria
from fichas_kv import kv_gib

# chave do `exige` (tecnicas.yaml) -> chave de `recursos` (entrada do usuario: True / False / None = nao informou)
RECURSOS = {"dados": "dados", "treino": "treino", "gpu_para_aplicar": "gpu"}
# preferencia -> movimentos que a favorecem. NAO exclui as demais tecnicas: a fronteira de Pareto mostra os dois lados.
FAVORECE = {"qualidade": {"Improve", "Grow"}, "footprint": {"Shrink", "Speed-up"}}
MARGEM = 0.20   # HIPOTESE (C): folga sobre o minimo teorico; sera trocada pelo fator de correcao medido por motor/arquitetura


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

def _porque(t, f, cat, recursos):
    """Regra e fonte de cada decisao (justificativa por passo)."""
    p = []
    for q in t["requer_modelo"]:
        nome = q if isinstance(q, str) else next(iter(q))
        p.append(f"modelo: {nome} = {_chamar(q, f, cat)}  [tecnicas.yaml:requer_modelo + fichas.json]")
    if t["aplica_em"] != "modelo_pronto": p.append(f"aplica_em = {t['aplica_em']}  [tecnicas.yaml]")
    for k, v in t["exige"].items():
        if v != "nao": p.append(f"recurso: exige {k} = {v}; usuario {RECURSOS[k]} = {recursos.get(RECURSOS[k])}  [tecnicas.yaml:exige]")
    return p

def candidatar(f, cat, T, recursos=None, preferencia=None):
    """Para um modelo: situacao de cada tecnica aplicavel a modelo pronto. status: True aplica | None talvez | False nao."""
    recursos = recursos or {}; out = []
    for k, t in T["tecnicas"].items():
        if t["aplica_em"] != "modelo_pronto": continue
        m, r = avalia(t, f, cat), avalia_recursos(t, recursos)
        out.append({"tecnica": k, "modelo": m, "recursos": r, "status": _e3([m, r]), "preferencia": preferencia_da(t, preferencia),
                    "medida_na_v1": t["medida_na_v1"], "tag_efeitos": t["tag_efeitos"], "porque": _porque(t, f, cat, recursos)})
    return out

def memoria_gib(f, ctx, bits_pesos=16, bits_kv=16):
    """Mínimo teórico: pesos de texto + KV (B; estado linear e k_eq_v são C). Em MoE, todos os especialistas ficam na memória."""
    n = f["params"].get("texto") or f["params"]["total"]
    return n * bits_pesos / 8 / 2 ** 30 + kv_gib(f, ctx, bytes_kv=bits_kv / 8)

def cabe(minimo, disponivel, margem=MARGEM):
    """False: nem o mínimo cabe | None: cabe sem folga | True: cabe com folga."""
    if minimo > disponivel: return False
    return True if minimo * (1 + margem) <= disponivel else None

def grade_memoria(f, T, ctx, disponivel_gib):
    """Combinações de bits de pesos x bits de KV (níveis do tecnicas.yaml + baseline 16)."""
    tec = T["tecnicas"]
    bp = [16] + [b for b in tec["quantizacao_pesos"]["niveis"]["valores"]]
    bk = list(tec["quantizacao_kv"]["niveis"]["valores"])
    return {(p, k): (m := memoria_gib(f, ctx, p, k), cabe(m, disponivel_gib)) for p in bp for k in bk}


# efeitos.csv
import csv, datetime, os

COLUNAS_EFEITOS = ["id", "modelo", "tecnicas", "ctx", "eixo", "benchmark", "metrica", "tipo_valor", "valor", "ic_baixo", "ic_alto",
                   "n", "hardware", "motor", "origem", "fonte_ref", "run_id", "data", "tag", "observacao"]
EIXOS = {"qualidade", "memoria", "disco", "latencia_decodificacao", "latencia_prefill"}


def parse_tecnicas(s, T):
    """'quantizacao_kv:8+quantizacao_pesos:4' -> [(id, nível)]; 'nenhuma' -> []."""
    if s == "nenhuma": return []
    out = []
    for par in s.split("+"):
        t, _, n = par.partition(":")
        valores = T["tecnicas"].get(t, {}).get("niveis", {}).get("valores")
        if isinstance(valores, list): n = next((v for v in valores if str(v) == n), n)
        out.append((t, n))
    return out


def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def validar_efeitos(caminho=None, benchmarks=None, runs=None, F=None, T=None):
    """Devolve a lista de erros (vazia = ok)."""
    if F is None or T is None: F, T = carregar()
    caminho = caminho or _achar("efeitos.csv")
    benchmarks = benchmarks or _achar("benchmarks_candidatos.csv")
    runs = runs or os.path.join(os.path.dirname(caminho), "runs")
    bench = {r["benchmark"] for r in csv.DictReader(open(benchmarks))}
    linhas = list(csv.DictReader(open(caminho)))
    cab = csv.DictReader(open(caminho)).fieldnames
    erros = [] if cab == COLUNAS_EFEITOS else [f"cabecalho diferente do esquema: {cab}"]
    vistos = {}
    for n, r in enumerate(linhas, start=2):
        e = lambda m: erros.append(f"linha {n}: {m}")
        f = F.get(r["modelo"])
        if not f: e(f"modelo fora do fichas.json: {r['modelo']}"); continue
        lista = parse_tecnicas(r["tecnicas"], T)
        try:
            ctx = int(r["ctx"]); config_id(r["modelo"], lista, ctx, T)
            if r["tecnicas"] != ("+".join(f"{t}:{v}" for t, v in sorted(lista)) or "nenhuma"): e("tecnicas fora da forma canonica (ordem alfabetica)")
        except (ValueError, KeyError) as ex: e(f"configuracao invalida: {ex}"); continue
        for t, _ in lista:
            if avalia(T["tecnicas"][t], f, F) is False: e(f"{t} nao se aplica a {r['modelo']}")
        if f["tipo"] == "hibrido" and "modo_raciocinio" not in [t for t, _ in lista]:
            e("modelo hibrido exige modo_raciocinio explicito (a linha base fica ambigua)")
        if r["eixo"] not in EIXOS: e(f"eixo invalido: {r['eixo']}"); continue
        if r["eixo"] == "qualidade":
            if r["benchmark"] not in bench: e(f"benchmark desconhecido: {r['benchmark']!r}")
        elif r["benchmark"]: e("benchmark so vale para o eixo qualidade")
        if r["eixo"] in ("memoria", "latencia_decodificacao", "latencia_prefill") and not (r["hardware"] and r["motor"]): e("memoria/latencia exigem hardware e motor")
        if r["eixo"] == "disco" and not r["motor"]: e("disco exige motor (o tamanho depende do formato/quantizador)")
        if not r["metrica"]: e("metrica vazia")
        if r["tipo_valor"] not in ("absoluto", "razao"): e("tipo_valor deve ser absoluto ou razao")
        if r["tipo_valor"] == "razao" and r["origem"] == "propria": e("razao so vale para paper/card; medicao propria entra como absoluto")
        v, lo, hi = _num(r["valor"]), _num(r["ic_baixo"]), _num(r["ic_alto"])
        if v is None: e("valor nao numerico")
        elif (r["ic_baixo"] or r["ic_alto"]) and not (lo is not None and hi is not None and lo <= v <= hi): e("intervalo deve ter ic_baixo <= valor <= ic_alto")
        if r["n"] and not (r["n"].isdigit() and int(r["n"]) >= 1): e("n deve ser inteiro >= 1")
        if r["origem"] not in ("propria", "paper", "card"): e("origem deve ser propria, paper ou card")
        if r["tag"] not in ("A", "B", "C"): e("tag deve ser A, B ou C")
        if r["origem"] == "card" and r["tag"] != "C": e("numero de model card entra com tag C")
        if r["origem"] == "propria":
            if not (r["run_id"] and r["n"] and r["motor"]): e("medicao propria exige run_id, n e motor")
            elif not os.path.exists(os.path.join(runs, r["run_id"] + ".json")): e(f"run_id sem arquivo em {runs}/: {r['run_id']}")
        if not r["fonte_ref"]: e("fonte_ref vazia")
        try: datetime.date.fromisoformat(r["data"])
        except ValueError: e("data deve ser AAAA-MM-DD")
        chave = (r["modelo"], r["tecnicas"], r["ctx"], r["eixo"], r["benchmark"], r["hardware"], r["motor"], r["origem"], r["run_id"] or r["fonte_ref"])
        if chave in vistos: e(f"duplicada da linha {vistos[chave]}")
        vistos.setdefault(chave, n)
    return erros


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
    if _achar("efeitos.csv", obrigatorio=False): erros += validar_efeitos(F=F, T=T)
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
