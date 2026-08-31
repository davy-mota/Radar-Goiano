from fastapi import APIRouter

from .cache_utils import carregar_cache

router = APIRouter()
@router.get("/api/diarias/resumo")
def get_resumo_diarias(ano: str = "todos"):
    return carregar_cache("diarias", ano)
