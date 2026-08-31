from fastapi import APIRouter

from .cache_utils import carregar_cache

router = APIRouter()

@router.get("/api/contratos/resumo")
def get_resumo_contratos(ano: str = "todos"):
    return carregar_cache("contratos", ano)
