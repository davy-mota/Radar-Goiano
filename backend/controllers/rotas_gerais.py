from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter()

@router.get("/api/geral/resumo")
def get_resumo_geral(ano: str = "todos"):
    caminho = Path(__file__).parent.parent / f"cache_visao_geral_{ano}.json"
    try:
        with open(caminho, 'r', encoding='utf-8') as f: 
            return json.load(f)
    except Exception as e: 
        return {"erro": f"Dados de Visão Geral para '{ano}' ainda não foram gerados."}