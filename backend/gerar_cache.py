"""Gera caches incrementais sem carregar registros brutos na memória."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text

from database import engine

BASE = Path(__file__).resolve().parent
DESTINOS = (BASE / "dados_gerados", BASE.parent / "frontend/radar-front/public/dados")
ANO_MINIMO = 2013


def _jsonavel(valor: Any) -> Any:
    return float(valor) if isinstance(valor, Decimal) else valor


def _filtro(ano: int | None, alias: str = "") -> tuple[str, dict[str, int]]:
    return ("", {}) if ano is None else (f" WHERE {alias}ano_exercicio = :ano", {"ano": ano})


class Banco:
    """Consultas com memória, paralelismo e duração limitados no PostgreSQL."""

    def __init__(self, timeout_minutos: int) -> None:
        self.timeout_ms = timeout_minutos * 60_000

    def listar(self, sql: str, parametros: dict | None = None) -> list[dict]:
        with engine.begin() as conexao:
            conexao.execute(text("SET LOCAL work_mem = '16MB'"))
            conexao.execute(text("SET LOCAL max_parallel_workers_per_gather = 1"))
            conexao.execute(text(f"SET LOCAL statement_timeout = '{self.timeout_ms}ms'"))
            resultado = conexao.execute(text(sql), parametros or {})
            return [
                {chave: _jsonavel(valor) for chave, valor in dict(linha).items()}
                for linha in resultado.mappings()
            ]

    def um(self, sql: str, parametros: dict | None = None) -> dict:
        linhas = self.listar(sql, parametros)
        return linhas[0] if linhas else {}


def _gravar_atomico(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(prefix=f".{caminho.name}.", suffix=".tmp", dir=caminho.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    except BaseException:
        try:
            os.unlink(temporario)
        except FileNotFoundError:
            pass
        raise


def _publicar(nome: str, dados: dict) -> None:
    for destino in DESTINOS:
        _gravar_atomico(destino / nome, dados)


def _alertas(linhas: list[dict], motivo: str) -> list[dict]:
    return [{
        "nome": linha.get("nome") or "Não informado",
        "orgao": linha.get("orgao") or "Não informado",
        "valor": float(linha.get("valor") or 0),
        "motivo": motivo,
    } for linha in linhas]


def gerar_periodo(ano: int | None, timeout_minutos: int = 15) -> list[str]:
    banco = Banco(timeout_minutos)
    sufixo = "todos" if ano is None else str(ano)
    filtro, params = _filtro(ano)
    and_ano = " AND ano_exercicio = :ano" if ano is not None else ""
    gerados: list[str] = []

    print(f"[1/4] Contratos — {sufixo}", flush=True)
    ck = banco.um(f"SELECT COALESCE(SUM(valor_contrato),0) total, COUNT(*) qtd, COALESCE(MAX(valor_contrato),0) maior FROM contratos_licitacoes{filtro}", params)
    ct = banco.listar(f"SELECT normalizar_texto_utf8(nome_contratado) nome, SUM(valor_contrato) valor FROM contratos_licitacoes{filtro} GROUP BY normalizar_texto_utf8(nome_contratado) ORDER BY valor DESC NULLS LAST LIMIT 10", params)
    cm = banco.listar(f"SELECT normalizar_texto_utf8(nome_contratado) nome, normalizar_texto_utf8(nome_orgao) orgao, valor_contrato valor FROM contratos_licitacoes{filtro} ORDER BY valor_contrato DESC NULLS LAST LIMIT 5", params)
    ef = banco.um(f"SELECT normalizar_texto_utf8(nome_contratado) nome, COUNT(*) qtd FROM contratos_licitacoes{filtro} GROUP BY normalizar_texto_utf8(nome_contratado) ORDER BY qtd DESC LIMIT 1", params)
    ctotal, cqtd = float(ck.get("total") or 0), int(ck.get("qtd") or 0)
    ca = _alertas(cm, "Maior valor individual do período; requer validação documental")
    nome = f"cache_contratos_{sufixo}.json"
    _publicar(nome, {"kpis": {"valor_total": ctotal, "qtd_contratos": cqtd, "ticket_medio": ctotal / cqtd if cqtd else 0}, "top_fornecedores": ct, "alertas_ia": ca})
    gerados.append(nome)

    print(f"[2/4] Folha — {sufixo}", flush=True)
    fk = banco.um(f"SELECT COALESCE(SUM(valor_remuneracao_bruta),0) total, COUNT(id) qtd, COALESCE(AVG(valor_remuneracao_bruta),0) media, COUNT(*) FILTER (WHERE valor_remuneracao_bruta > 41650.92) acima_teto FROM folha_pagamento WHERE valor_remuneracao_bruta > 0{and_ano}", params)
    ft = banco.listar(f"SELECT normalizar_texto_utf8(nome_servidor) nome, normalizar_texto_utf8(nome_orgao) orgao, valor_remuneracao_bruta valor FROM folha_pagamento{filtro} ORDER BY valor_remuneracao_bruta DESC NULLS LAST LIMIT 5", params)
    fo = banco.listar(f"SELECT normalizar_texto_utf8(nome_orgao) name, SUM(valor_remuneracao_bruta) value FROM folha_pagamento{filtro} GROUP BY normalizar_texto_utf8(nome_orgao) ORDER BY value DESC NULLS LAST LIMIT 5", params)
    ftotal = float(fk.get("total") or 0)
    fa = _alertas(ft, "Maior remuneração bruta individual do período; requer contextualização")
    nome = f"cache_folha_{sufixo}.json"
    _publicar(nome, {"kpis": {"total_folha": ftotal, "qtd_servidores": int(fk.get("qtd") or 0), "media_salarial": float(fk.get("media") or 0)}, "top_salarios": [{"nome": x["nome"], "valor": x["valor"]} for x in ft], "distribuicao": fo, "alertas_ia": fa})
    gerados.append(nome)

    print(f"[3/4] Diárias — {sufixo}", flush=True)
    dk = banco.um(f"SELECT COALESCE(SUM(valor_total),0) total, COUNT(id) qtd, COALESCE(MAX(valor_total),0) maior FROM diarias_passagens{filtro}", params)
    dv = banco.listar(f"SELECT normalizar_texto_utf8(nome_servidor) nome, SUM(valor_total) valor FROM diarias_passagens{filtro} GROUP BY normalizar_texto_utf8(nome_servidor) ORDER BY valor DESC NULLS LAST LIMIT 5", params)
    dd = banco.listar(f"SELECT normalizar_texto_utf8(destino) name, SUM(valor_total) value FROM diarias_passagens{filtro} GROUP BY normalizar_texto_utf8(destino) ORDER BY value DESC NULLS LAST LIMIT 5", params)
    dm = banco.listar(f"SELECT normalizar_texto_utf8(nome_servidor) nome, normalizar_texto_utf8(destino) orgao, valor_total valor FROM diarias_passagens{filtro} ORDER BY valor_total DESC NULLS LAST LIMIT 5", params)
    dtotal = float(dk.get("total") or 0)
    da = _alertas(dm, "Maior valor individual de diária do período; requer validação documental")
    nome = f"cache_diarias_{sufixo}.json"
    _publicar(nome, {"kpis": {"total_gasto": dtotal, "qtd_viagens": int(dk.get("qtd") or 0), "maior_diaria": float(dk.get("maior") or 0)}, "top_viajantes": dv, "top_destinos": dd, "alertas_ia": da})
    gerados.append(nome)

    print(f"[4/4] Visão geral — {sufixo}", flush=True)
    ff, fp = _filtro(ano, "f.")
    df, _ = _filtro(ano, "d.")
    orgaos = banco.listar(f"SELECT nome, SUM(total) total FROM (SELECT normalizar_texto_utf8(f.nome_orgao) nome, SUM(f.valor_remuneracao_bruta) total FROM folha_pagamento f{ff} GROUP BY normalizar_texto_utf8(f.nome_orgao) UNION ALL SELECT normalizar_texto_utf8(d.nome_orgao) nome, SUM(d.valor_total) total FROM diarias_passagens d{df} GROUP BY normalizar_texto_utf8(d.nome_orgao)) gastos GROUP BY nome ORDER BY total DESC NULLS LAST LIMIT 5", fp)
    radar = []
    if fa: radar.append({**fa[0], "tipo": "Folha"})
    if ca: radar.append({**ca[0], "tipo": "Contratos"})
    if da: radar.append({**da[0], "tipo": "Diárias"})
    nome = f"cache_visao_geral_{sufixo}.json"
    _publicar(nome, {"kpis": {"custo_total": ctotal + ftotal + dtotal, "orgao_campeao": orgaos[0]["nome"] if orgaos else "N/A", "maior_despesa": float(ck.get("maior") or 0), "alerta_teto": int(fk.get("acima_teto") or 0)}, "raio_x": [{"name": "Folha", "value": ftotal}, {"name": "Contratos", "value": ctotal}, {"name": "Diárias", "value": dtotal}], "top_orgaos": orgaos, "anomalias": {"maior_viajante": dv[0] if dv else {"nome": "N/A", "valor": 0}, "empresa_favorita": ef if ef else {"nome": "N/A", "qtd": 0}}, "radar_ia_geral": radar})
    gerados.append(nome)
    return gerados


def main() -> int:
    parser = argparse.ArgumentParser(description="Gerador de caches JSON com memória limitada")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--ano", type=int, help="Gera um único exercício (recomendado)")
    grupo.add_argument("--consolidado", action="store_true", help="Gera somente o cache 'todos'")
    grupo.add_argument("--todos-os-anos", action="store_true", help="Gera todos sequencialmente")
    parser.add_argument("--ano-final", type=int, default=datetime.now().year)
    parser.add_argument("--timeout-minutos", type=int, default=15)
    args = parser.parse_args()
    if args.timeout_minutos < 1:
        parser.error("--timeout-minutos deve ser maior que zero")
    if args.ano is not None:
        if not ANO_MINIMO <= args.ano <= args.ano_final:
            parser.error(f"--ano deve estar entre {ANO_MINIMO} e {args.ano_final}")
        periodos: list[int | None] = [args.ano]
    elif args.consolidado:
        periodos = [None]
    else:
        periodos = [None, *range(ANO_MINIMO, args.ano_final + 1)]
    for indice, ano in enumerate(periodos, 1):
        rotulo = "todos" if ano is None else ano
        print(f"\n=== Período {rotulo} ({indice}/{len(periodos)}) ===", flush=True)
        print("Concluído: " + ", ".join(gerar_periodo(ano, args.timeout_minutos)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
