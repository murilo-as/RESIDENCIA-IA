"""Regra de memoria de KV por tipo de atencao, a partir de uma ficha de fichas.json.

Teorico (minimo). O motor pode alocar mais; a diferenca vira fator de correcao medido no Spark.
Tags: camadas completa/janela/compartilhada = B ; estado linear = C ; k_eq_v = C (a confirmar).
"""


def kv_bytes(ficha, ctx, bytes_kv=2.0, bytes_estado_linear=4.0, bytes_conv=2.0):
    """Retorna dict com bytes de cache para `ctx` tokens (batch 1)."""
    a = ficha["arquitetura"]
    c = a["camadas_proprias"]            # camadas que guardam cache proprio, por tipo
    kvh, hd = a["kv_heads"], a["head_dim"]
    kvh_g = a.get("global_kv_heads") or kvh
    hd_g = a.get("global_head_dim") or hd
    fator_kv = 1 if a.get("k_eq_v") else 2      # K e V guardados uma so vez se k_eq_v (hipotese)

    completa = c.get("full_attention", 0) * fator_kv * kvh_g * hd_g * bytes_kv * ctx
    janela = a.get("janela")
    deslizante = 0.0
    if c.get("sliding_attention", 0):
        n_tok = min(ctx, janela) if janela else ctx
        deslizante = c["sliding_attention"] * 2 * kvh * hd * bytes_kv * n_tok
    linear = 0.0
    lin = a.get("linear")
    if c.get("linear_attention", 0) and lin:
        estado = lin["v_heads"] * lin["k_dim"] * lin["v_dim"] * bytes_estado_linear
        conv = (lin["conv_kernel"] - 1) * (2 * lin["k_heads"] * lin["k_dim"] + lin["v_heads"] * lin["v_dim"]) * bytes_conv
        linear = c["linear_attention"] * (estado + conv)     # constante: nao cresce com ctx
    total = completa + deslizante + linear
    return {"completa": completa, "janela": deslizante, "linear_const": linear, "total": total}


def kv_gib(ficha, ctx, **kw):
    return kv_bytes(ficha, ctx, **kw)["total"] / 2 ** 30


def pesos_gib(ficha, bits_por_peso=16.0):
    return ficha["params"]["total"] * bits_por_peso / 8 / 2 ** 30
