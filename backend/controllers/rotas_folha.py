from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter()
@router.get("/api/folha/resumo")
def get_resumo_folha(ano: str = "todos"):
    caminho = Path(__file__).parent.parent / f"cache_folha_{ano}.json"
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {"erro": f"Dados de Folha para '{ano}' ainda não foram gerados."}