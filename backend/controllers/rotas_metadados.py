from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database import engine


router = APIRouter(prefix="/api/metadados", tags=["qualidade e proveniência"])

CONFIGURACAO = {
    "pagamentos": ("Empenhos e pagamentos", "https://transparencia.go.gov.br/dados-abertos/"),
    "receitas": ("Receitas estaduais", "https://dadosabertos.go.gov.br/"),
    "contratos": ("Contratos", "https://dadosabertos.go.gov.br/"),
    "folha": ("Folha de pagamento", "https://dadosabertos.go.gov.br/"),
    "diarias": ("Diárias", "https://dadosabertos.go.gov.br/"),
}


@router.get("")
def metadados_dos_conjuntos():
    try:
        with engine.connect() as conexao:
            linhas = conexao.execute(text("""
                SELECT conjunto, registros, ano_min, ano_max, maior_data_referencia,
                       qualidade, calculado_em
                FROM metadados_qualidade
                ORDER BY conjunto
            """)).mappings().all()
    except Exception as erro:
        raise HTTPException(
            status_code=503,
            detail="Metadados indisponíveis. Execute a migração 006.",
        ) from erro

    conjuntos_por_id = {linha["conjunto"]: dict(linha) for linha in linhas}
    conjuntos = []
    for identificador, (nome, fonte) in CONFIGURACAO.items():
        if identificador not in conjuntos_por_id:
            continue
        conjunto = conjuntos_por_id[identificador]
        conjunto.update({"id": identificador, "nome": nome, "fonte": fonte})
        conjuntos.append(conjunto)

    return {
        "conjuntos": conjuntos,
        "observacao": (
            "As métricas foram materializadas no horário indicado por calculado_em. "
            "Maior data de referência pertence ao dado, não ao processo de extração."
        ),
    }
