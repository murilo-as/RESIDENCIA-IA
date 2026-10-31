"""3.1: tenta carregar 1 exemplo do GPQA Diamond com o HF_TOKEN do ambiente. Imprime so 'sucesso' ou o tipo do erro (nunca o token nem o conteudo da questao)."""
from datasets import load_dataset
try:
    ds = load_dataset("Idavidrein/gpqa", "gpqa_diamond", split="train[:1]")
    print("sucesso: 1 exemplo carregado")
except Exception as e:
    print(f"falha: {type(e).__name__} (termos do dataset nao aceitos, token sem acesso ou sem rede; mensagem omitida)")
