"""Carga versionada da execução por função e natureza da despesa."""
import hashlib
import io
import json
import re

import pandas as pd
import requests
from sqlalchemy import text

from database import engine

PACOTE = "execucao-orcamentaria-natureza-despesa"
CKAN = "https://dadosabertos.go.gov.br/api/3/action/package_show"

MAPA = {
    "codigo_orgao": "CODG_ORGAO", "nome_orgao": "NOME_ORGAO_REDUZIDO_ATUAL",
    "codigo_funcao": "CODG_FUNCAO", "nome_funcao": "NOME_FUNCAO",
    "codigo_subfuncao": "CODG_SUBFUNCAO", "nome_subfuncao": "NOME_SUBFUNCAO",
    "codigo_programa": "CODG_PROGRAMA_DOTACAO", "nome_programa": "NOME_PROGRAMA_DOTACAO",
    "codigo_acao": "CODG_ACAO_DOTACAO", "nome_acao": "NOME_ACAO_DOTACAO",
    "codigo_categoria": "CODG_CATEGORIA_ECONOMICA", "nome_categoria": "NOME_CATEGORIA_ECONOMICA",
    "codigo_grupo": "CODG_GRUPO_DESPESA", "nome_grupo": "NOME_GRUPO_DESPESA",
    "codigo_modalidade": "CODG_MODALIDADE_APLICACAO", "nome_modalidade": "NOME_MODALIDADE_APLICACAO",
    "codigo_elemento": "CODG_ELEMENTO_DESPESA", "nome_elemento": "NOME_ELEMENTO_DESPESA",
}

def recursos_mensais(ano: int) -> list[dict]:
    resposta = requests.get(CKAN, params={"id": PACOTE}, timeout=60)
    resposta.raise_for_status()
    recursos = []
    for item in resposta.json()["result"]["resources"]:
        nome = item.get("name", "")
        achado = re.search(rf"(Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro)/{ano}", nome)
        if achado and item.get("format", "").upper() == "CSV":
            recursos.append(item)
    return sorted(recursos, key=lambda r: r["name"])

def carregar(ano: int) -> int:
    recursos = recursos_mensais(ano)
    if not recursos:
        raise RuntimeError(f"Nenhum recurso mensal oficial encontrado para {ano}.")
    with engine.begin() as c:
        lote = c.execute(text("INSERT INTO lotes_execucao_orcamentaria(status, recursos) VALUES ('preparando', CAST(:r AS jsonb)) RETURNING id"), {"r": json.dumps([{"id": r["id"], "nome": r["name"], "url": r["url"], "modificado_em": r.get("last_modified")} for r in recursos])}).scalar_one()
    total = 0
    try:
        for recurso in recursos:
            bruto = requests.get(recurso["url"], timeout=120).content
            quadro = pd.read_csv(io.BytesIO(bruto), sep=";", dtype=str, encoding="utf-8", encoding_errors="replace").fillna("")
            registros = []
            for linha in quadro.to_dict("records"):
                mes = int(linha["NUMR_MES"])
                exercicio = int(linha["NUMR_ANO_EXERCICIO"])
                if exercicio != ano or not 1 <= mes <= 12:
                    raise ValueError(f"Período inválido em {recurso['name']}: {exercicio}/{mes}")
                registro = {destino: linha.get(origem, "").strip() for destino, origem in MAPA.items()}
                registro.update(lote_id=lote, recurso_id=recurso["id"], ano_exercicio=exercicio, mes=mes,
                    valor_empenhado=float(linha["VALOR_EMPENHO"] or 0), valor_liquidado=float(linha["VALR_LIQUIDADO"] or 0), valor_pago=float(linha["VALOR_PAGO"] or 0))
                registro["chave_conteudo"] = hashlib.sha256(json.dumps(registro, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                registros.append(registro)
            colunas = list(registros[0])
            sql = text(f"INSERT INTO fatos_execucao_orcamentaria ({','.join(colunas)}) VALUES ({','.join(':'+c for c in colunas)}) ON CONFLICT DO NOTHING")
            with engine.begin() as c:
                for inicio in range(0, len(registros), 1000): c.execute(sql, registros[inicio:inicio+1000])
            total += len(registros)
        with engine.begin() as c:
            metricas = c.execute(text("SELECT COUNT(*) registros, COUNT(DISTINCT mes) meses, COALESCE(SUM(valor_pago),0) pago FROM fatos_execucao_orcamentaria WHERE lote_id=:id"), {"id": lote}).mappings().one()
            if metricas["meses"] != len(recursos) or metricas["registros"] == 0: raise ValueError("Cobertura da carga diverge dos recursos selecionados.")
            c.execute(text("UPDATE lotes_execucao_orcamentaria SET status='arquivado' WHERE status='ativo'"))
            c.execute(text("UPDATE lotes_execucao_orcamentaria SET status='ativo', finalizado_em=now(), metricas=CAST(:m AS jsonb) WHERE id=:id"), {"id": lote, "m": json.dumps(dict(metricas), default=float)})
        return lote
    except Exception as erro:
        with engine.begin() as c: c.execute(text("UPDATE lotes_execucao_orcamentaria SET status='rejeitado', finalizado_em=now(), observacao=:e WHERE id=:id"), {"id": lote, "e": str(erro)[:2000]})
        raise

if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--ano", type=int, required=True); a=p.parse_args()
    print(f"Lote ativo: {carregar(a.ano)}")
