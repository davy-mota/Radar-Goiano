from fastapi import APIRouter

from .cache_utils import carregar_cache

router = APIRouter()

@router.get("/api/geral/resumo")
def get_resumo_geral(ano: str = "todos"):
    return carregar_cache("visao_geral", ano)
