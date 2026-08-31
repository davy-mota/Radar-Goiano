import json
from pathlib import Path

from fastapi import HTTPException


CACHE_DIR = Path(__file__).resolve().parent.parent / "dados_gerados"
ANOS_VALIDOS = {"todos", *(str(ano) for ano in range(2013, 2027))}


def carregar_cache(prefixo: str, ano: str) -> dict:
    if ano not in ANOS_VALIDOS:
        raise HTTPException(status_code=422, detail="Ano inválido.")

    caminho = CACHE_DIR / f"cache_{prefixo}_{ano}.json"
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError as erro:
        raise HTTPException(
            status_code=404,
            detail=f"Dados de {prefixo} para '{ano}' ainda não foram gerados.",
        ) from erro
    except json.JSONDecodeError as erro:
        raise HTTPException(
            status_code=500,
            detail=f"O cache de {prefixo} para '{ano}' está inválido.",
        ) from erro
