"""Aplica a política de privacidade aos caches públicos já gerados."""

import json
from pathlib import Path

from sqlalchemy import text

from database import engine
from gerar_cache import _gravar_atomico
from privacidade import anonimizar_nome_pessoa


BASE = Path(__file__).resolve().parent
DIRETORIOS = (
    BASE / "dados_gerados",
    BASE.parent / "frontend/radar-front/public/dados",
)


def _nomes_figuras_publicas() -> dict[str, str]:
    consulta = text("""
        SELECT DISTINCT normalizar_texto_utf8(nome_servidor) AS nome
        FROM folha_pagamento
        WHERE UPPER(COALESCE(cargo, '')) ~ '(GOVERNADOR|DEPUTADO|SENADOR)'
        UNION
        SELECT DISTINCT normalizar_texto_utf8(nome_servidor) AS nome
        FROM diarias_passagens
        WHERE UPPER(COALESCE(cargo, '')) ~ '(GOVERNADOR|DEPUTADO|SENADOR)'
    """)
    with engine.begin() as conexao:
        conexao.execute(text("SET LOCAL statement_timeout = '10min'"))
        conexao.execute(text("SET LOCAL work_mem = '16MB'"))
        nomes = [nome for nome in conexao.execute(consulta).scalars() if nome]
    return {anonimizar_nome_pessoa(nome).casefold(): nome for nome in nomes}


def _anonimizar_item(item: dict, figuras_publicas: dict[str, str]) -> None:
    if item.get("nome"):
        chave = anonimizar_nome_pessoa(item["nome"]).casefold()
        item["nome"] = figuras_publicas.get(chave, anonimizar_nome_pessoa(item["nome"]))


def anonimizar_cache(caminho: Path, figuras_publicas: dict[str, str]) -> bool:
    dados = json.loads(caminho.read_text(encoding="utf-8"))

    if caminho.name.startswith("cache_folha_"):
        for item in dados.get("top_salarios", []):
            _anonimizar_item(item, figuras_publicas)
        for item in dados.get("alertas_ia", []):
            _anonimizar_item(item, figuras_publicas)
    elif caminho.name.startswith("cache_diarias_"):
        for item in dados.get("top_viajantes", []):
            _anonimizar_item(item, figuras_publicas)
        for item in dados.get("alertas_ia", []):
            _anonimizar_item(item, figuras_publicas)
    elif caminho.name.startswith("cache_visao_geral_"):
        _anonimizar_item(dados.get("anomalias", {}).get("maior_viajante", {}), figuras_publicas)
        for item in dados.get("radar_ia_geral", []):
            if item.get("tipo") in {"Folha", "Diárias"}:
                _anonimizar_item(item, figuras_publicas)
    else:
        return False

    _gravar_atomico(caminho, dados)
    return True


def main() -> int:
    alterados = 0
    figuras_publicas = _nomes_figuras_publicas()
    for diretorio in DIRETORIOS:
        if not diretorio.exists():
            continue
        for caminho in diretorio.glob("cache_*.json"):
            alterados += int(anonimizar_cache(caminho, figuras_publicas))
    print(f"Caches anonimizados: {alterados}; figuras públicas preservadas: {len(figuras_publicas)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
