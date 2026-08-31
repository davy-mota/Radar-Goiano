from fastapi import APIRouter

from .cache_utils import carregar_cache

router = APIRouter()
@router.get("/api/folha/resumo")
def get_resumo_folha(ano: str = "todos"):
    return carregar_cache("folha", ano)
