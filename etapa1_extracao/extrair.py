"""Etapa 1 - Extracao: texto livre -> pedido.json.

Regra de ouro: o LLM so EXTRAI (valor + trecho literal do texto). Toda decisao fica no codigo:
  - valor sem evidencia literal no texto -> descartado (vira vazio) e registrado em `avisos`;
  - mencao de modelo -> id do fichas.json por regra deterministica (nao pelo LLM);
  - mencao de hardware -> id do hardware.json, se o arquivo existir;
  - campos vazios continuam vazios: os padroes (ex.: tarefa vazia = Uso geral) sao da etapa 2.

Backends do LLM:
  llamacpp  -> llama-cpp-python com um .gguf local (usado nos testes)
  openai    -> qualquer servidor compativel com a API OpenAI (llama-server no Spark, Ollama, API externa)
  gemini    -> API do Gemini (chave em GEMINI_API_KEY)
  gabarito  -> devolve a anotacao do caso (testa so o pos-processamento, sem LLM)

Uso:
  python extrair.py --backend gemini --modelo NOME_DO_MODELO "quero um modelo ..."
  python extrair.py --backend llamacpp --modelo llm/qwen2.5-1.5b-instruct-q4_k_m.gguf "quero um modelo ..."
  python extrair.py --backend openai --url http://localhost:8080/v1 --modelo qwen "quero um modelo ..."
"""
import argparse, json, os, re, sys, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
def _achar(nome):
    """Procura o arquivo na pasta da etapa, em data/ ao lado dela e em ../data (dados compartilhados)."""
    for p in (os.path.join(AQUI, nome), os.path.join(AQUI, "data", nome), os.path.join(AQUI, "..", "data", nome)):
        if os.path.exists(p): return p
    return os.path.join(AQUI, nome)

SCHEMA = json.load(open(_achar("pedido.schema.json")))
NOMES = {"Codigo": "Código", "Traducao": "Tradução", "saude": "saúde", "juridico": "jurídico",
         "ciencia": "ciência", "matematica": "matemática"}      # valor interno (ASCII) -> nome de exibicao

PROMPT = """Extraia campos do TEXTO do usuário. Responda só com o JSON do esquema.
Cada campo tem "valor" e "evidencia". "evidencia" = trecho copiado palavra por palavra do TEXTO.
REGRA PRINCIPAL: preencha um campo só se o TEXTO o diz de forma explícita. Não deduza, não suponha, não complete por bom senso. Na dúvida: valor null e evidencia null. O trecho de evidência precisa dizer diretamente o que o valor afirma.

Campos:
- modelo: nome de modelo de linguagem citado no TEXTO (um nome próprio, não uma descrição como "um modelo pequeno").
- tarefa: QA (perguntas e respostas), Uso geral (assistente, resumir, escrever), Codigo (programar), Traducao (traduzir). Só se o TEXTO descrever o que o modelo vai fazer.
- dominio: geral, saude, juridico, ciencia, matematica ou outro. Só se o TEXTO indicar o assunto.
- hardware: máquina ou placa citada no TEXTO.
- memoria_gb: número de GB de memória, só se o TEXTO disser o número.
- preferencia: só se o TEXTO pedir isso explicitamente. "qualidade" = quer a melhor resposta/precisão, aceita lentidão. "footprint" = quer algo mais rápido, leve, pequeno ou com pouca memória. Elogios vagos como "bom" não contam.
- recursos.dados: true/false só se o TEXTO disser se tem ou não tem dados próprios.
- recursos.treino: true/false só se o TEXTO disser se pode ou não treinar ou ajustar o modelo. Ter ou não ter dados não responde isto.
- recursos.gpu: true/false só se o TEXTO falar de placa de vídeo, GPU ou VRAM. O nome de uma máquina não conta.
- entrada_longa: true só se o TEXTO diz que os textos de entrada são longos. O tipo de documento, ou ter muitos exemplos, não conta.
- raciocinio: true/false só se o TEXTO pedir (ou recusar) raciocínio passo a passo.
- idioma: idioma em que o TEXTO está escrito (pt, en, outro); evidencia = uma ou duas palavras copiadas do TEXTO."""


# ---------------- LLM ----------------
def chamar_llm(texto, backend, modelo=None, url=None, _cache={}):
    msgs = [{"role": "system", "content": PROMPT}, {"role": "user", "content": "TEXTO DO USUÁRIO:\n<<<\n" + texto + "\n>>>"}]
    if backend == "llamacpp":
        from llama_cpp import Llama
        if modelo not in _cache:
            _cache[modelo] = Llama(model_path=modelo, n_ctx=4096, seed=0, verbose=False)
        r = _cache[modelo].create_chat_completion(messages=msgs, temperature=0.0, seed=0,
                                                  response_format={"type": "json_object", "schema": SCHEMA})
        return json.loads(r["choices"][0]["message"]["content"])
    if backend == "openai":
        import urllib.request
        corpo = {"model": modelo, "messages": msgs, "temperature": 0, "seed": 0,
                 "response_format": {"type": "json_schema", "json_schema": {"name": "pedido", "schema": SCHEMA, "strict": True}}}
        req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=json.dumps(corpo).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + os.environ.get("LLM_API_KEY", "x")})
        r = json.load(urllib.request.urlopen(req, timeout=300))
        return json.loads(r["choices"][0]["message"]["content"])
    if backend == "gemini":
        import urllib.request
        esquema = {k: v for k, v in SCHEMA.items() if k != "$schema"}
        corpo = {"systemInstruction": {"parts": [{"text": PROMPT}]},
                 "contents": [{"role": "user", "parts": [{"text": msgs[1]["content"]}]}],
                 "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseJsonSchema": esquema}}
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
                                     data=json.dumps(corpo).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        import time, urllib.error
        for tentativa in range(4):          # repete em erro temporario da API (429/5xx) ou JSON invalido
            try:
                r = json.load(urllib.request.urlopen(req, timeout=120))
                return json.loads(r["candidates"][0]["content"]["parts"][0]["text"])
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 503) or tentativa == 3:
                    raise RuntimeError(f"Gemini HTTP {e.code}: {e.read().decode()[:300]}")
            except (json.JSONDecodeError, KeyError, IndexError):
                if tentativa == 3: raise
            time.sleep(2 ** tentativa)
    raise ValueError(f"backend desconhecido: {backend}")


# ---------------- pos-processamento (decisoes do codigo) ----------------
def _norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()

def _compacto(s):
    return re.sub(r"[^a-z0-9]", "", _norm(s))

def tem_evidencia(evid, texto):
    return bool(evid) and _norm(evid) in _norm(texto)

def resolver_modelo(mencao, fichas):
    """Mencao -> id do fichas.json. Regra (B): nome compactado (so letras e digitos) igual ao do id, ou prefixo dele;
    com varios candidatos, prefere quem nao e 'base' (o usuario final usa modelo pronto para conversa)."""
    alvo = _compacto(mencao)
    if not alvo: return None, [], "mencao vazia"
    cands = [i for i in fichas if _compacto(i.split("/")[1]).startswith(alvo)]
    if not cands: return None, [], "nenhum modelo do catalogo corresponde"
    exatos = [i for i in cands if _compacto(i.split("/")[1]) == alvo]
    if len(exatos) == 1: return exatos[0], cands, "nome exato"
    nao_base = [i for i in cands if fichas[i]["tipo"] != "base"]
    if len(nao_base) == 1: return nao_base[0], cands, "prefixo; preferido o modelo nao-base"
    return None, cands, "ambiguo: varios candidatos"

def resolver_hardware(mencao, caminho=None):
    caminho = caminho or _achar("hardware.json")
    if not os.path.exists(caminho): return None, "hardware.json ainda nao existe"
    hw = json.load(open(caminho))
    alvo = _compacto(mencao)
    achados = [k for k, v in hw.items() if alvo and (alvo in _compacto(k) or any(alvo in _compacto(a) for a in v.get("apelidos", [])))]
    return (achados[0], "correspondencia por nome") if len(achados) == 1 else (None, f"{len(achados)} correspondencias")


def pos_processar(texto, bruto, fichas):
    avisos, pedido = [], {"texto": texto}

    def campo(nome, item, exibir=lambda v: v):
        v, ev = item.get("valor"), item.get("evidencia")
        if v is None:
            return {"valor": None, "evidencia": None, "origem": "vazio"}
        if not tem_evidencia(ev, texto):
            avisos.append(f"{nome}: valor {v!r} descartado (evidencia {ev!r} nao esta no texto)")
            return {"valor": None, "evidencia": None, "origem": "descartado"}
        return {"valor": exibir(v), "evidencia": ev, "origem": "texto"}

    for nome in ("tarefa", "dominio", "preferencia", "idioma"):
        pedido[nome] = campo(nome, bruto[nome], lambda v: NOMES.get(v, v))
    for nome in ("entrada_longa", "raciocinio"):
        pedido[nome] = campo(nome, bruto[nome])
    pedido["recursos"] = {k: campo(f"recursos.{k}", bruto["recursos"][k]) for k in ("dados", "treino", "gpu")}

    m = campo("memoria_gb", bruto["memoria_gb"])
    if m["valor"] is not None and not re.search(rf"(?<!\d){re.escape(str(int(m['valor'])) if float(m['valor']).is_integer() else str(m['valor']))}(?!\d)", m["evidencia"]):
        avisos.append(f"memoria_gb: {m['valor']} nao aparece na evidencia {m['evidencia']!r}; descartado")
        m = {"valor": None, "evidencia": None, "origem": "descartado"}
    pedido["memoria_gb"] = m

    mo = campo("modelo", bruto["modelo"])
    if mo["valor"]:
        mo["id"], mo["candidatos"], mo["regra"] = resolver_modelo(mo["valor"], fichas)
        if not mo["id"]: avisos.append(f"modelo: {mo['valor']!r} nao resolvido ({mo['regra']}; candidatos: {mo['candidatos'][:5]})")
    pedido["modelo"] = mo

    hw = campo("hardware", bruto["hardware"])
    if hw["valor"]:
        hw["id"], hw["regra"] = resolver_hardware(hw["valor"])
    pedido["hardware"] = hw

    pedido["avisos"] = avisos
    return pedido


def sanear(bruto):
    """Valida o JSON do LLM contra o schema. Um `valor` invalido (ex.: tarefa = 'Matematica', fora da lista)
    e trocado por vazio e registrado em avisos; so levanta erro se a ESTRUTURA estiver quebrada."""
    import jsonschema
    avisos = []
    for _ in range(40):
        erros = list(jsonschema.Draft7Validator(SCHEMA).iter_errors(bruto))
        if not erros: return avisos
        e = erros[0]; caminho = list(e.absolute_path)
        if len(caminho) < 2 or caminho[-1] != "valor":
            raise jsonschema.ValidationError(f"estrutura invalida em {caminho}: {e.message}")
        no = bruto
        for k in caminho[:-1]: no = no[k]
        avisos.append(f"{'.'.join(map(str, caminho[:-1]))}: valor {no['valor']!r} fora do formato; descartado")
        no["valor"] = None; no["evidencia"] = None
    raise RuntimeError("sanear: erros demais")


def extrair(texto, backend="llamacpp", modelo=None, url=None, bruto=None, fichas=None):
    fichas = fichas or json.load(open(_achar("fichas.json")))["fichas"]
    if bruto is None: bruto = chamar_llm(texto, backend, modelo, url)
    avisos_formato = sanear(bruto)              # valor fora do formato vira vazio (nao derruba o pedido inteiro)
    p = pos_processar(texto, bruto, fichas)
    p["avisos"] = avisos_formato + p["avisos"]
    return p


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("texto"); ap.add_argument("--backend", default="llamacpp")
    ap.add_argument("--modelo"); ap.add_argument("--url")
    a = ap.parse_args()
    print(json.dumps(extrair(a.texto, a.backend, a.modelo, a.url), ensure_ascii=False, indent=1))