from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from typing import Literal

from database import engine


router = APIRouter(prefix="/api/cargas", tags=["observabilidade"])


@router.get("")
def listar_cargas(
    conjunto: Literal["pagamentos", "receitas", "contratos", "folha", "diarias"] | None = None,
    limite: int = Query(default=20, ge=1, le=100),
):
    parametros = {"limite": limite}
    filtro = ""
    if conjunto:
        filtro = "WHERE conjunto = :conjunto"
        parametros["conjunto"] = conjunto

    try:
        with engine.connect() as conexao:
            linhas = conexao.execute(text(f"""
                SELECT id, conjunto, status, fonte, iniciado_em, finalizado_em,
                       registros_processados, duracao_segundos, mensagem_erro
                FROM historico_cargas
                {filtro}
                ORDER BY iniciado_em DESC
                LIMIT :limite
            """), parametros).mappings().all()
    except Exception as erro:
        raise HTTPException(status_code=503, detail="Histórico de cargas indisponível. Execute a migração 007.") from erro

    return {"cargas": [dict(linha) for linha in linhas]}
