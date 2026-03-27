from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter()
@router.get("/api/diarias/resumo")
def get_resumo_diarias(ano: str = "todos"):
    caminho = Path(__file__).parent.parent / f"cache_diarias_{ano}.json"
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {"erro": f"Dados de Diárias para '{ano}' ainda não foram gerados."}