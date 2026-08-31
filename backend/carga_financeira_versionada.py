import argparse
import hashlib
import json
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import text

from database import engine


CATALOGOS = {
    "empenhos": "empenhos",
    "liquidacoes": "liquidacoes",
    "pagamentos": "pagamentos",
    "receitas": "receitas-detalhadas",
}
TABELAS = {
    "empenhos": "fatos_empenhos",
    "liquidacoes": "fatos_liquidacoes",
    "pagamentos": "fatos_pagamentos",
    "receitas": "fatos_receitas",
}


def nome_normalizado(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", texto.upper()).strip("_")


def selecionar_recursos(recursos: list[dict], ano: int | None = None) -> list[dict]:
    candidatos = [r for r in recursos if str(r.get("format", "")).upper() in {"CSV", "ZIP"}]
    anuais = []
    mensais = []
    for recurso in candidatos:
        nome = recurso.get("name", "")
        formato = recurso.get("format", "").upper()
        anos_no_nome = re.findall(r"20\d{2}", nome)
        if len(set(anos_no_nome)) != 1:
            continue
        anual = re.search(r"\s-\s(20\d{2})\s*$", nome)
        mensal = re.search(r"(20\d{2})\s*$", nome)
        if formato == "ZIP" and anual:
            anuais.append((int(anual.group(1)), recurso))
        elif formato == "CSV" and mensal:
            mensais.append((int(mensal.group(1)), recurso))

    anos_anuais = {item[0] for item in anuais}
    if ano is not None:
        escolhidos = [r for a, r in anuais if a == ano]
        if not escolhidos:
            escolhidos = [r for a, r in mensais if a == ano]
        return sorted(escolhidos, key=lambda r: r.get("name", ""))

    maior_anual = max(anos_anuais, default=0)
    escolhidos = [r for _, r in anuais]
    escolhidos.extend(r for a, r in mensais if a > maior_anual)
    return sorted(escolhidos, key=lambda r: r.get("name", ""))


def moeda(serie: pd.Series) -> pd.Series:
    def converter(valor):
        texto_valor = str(valor).strip().replace('"', "").replace("'", "")
        if texto_valor.lower() in {"", "nan", "none"}:
            return 0.0
        if "," in texto_valor:
            texto_valor = texto_valor.replace(".", "").replace(",", ".")
        elif texto_valor.count(".") > 1:
            texto_valor = texto_valor.replace(".", "")
        try:
            return round(float(texto_valor), 2)
        except ValueError:
            return 0.0
    return serie.map(converter)


def mes_numerico(serie: pd.Series) -> pd.Series:
    meses = {
        "JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6,
        "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12,
    }
    numerico = pd.to_numeric(serie, errors="coerce")
    texto = serie.astype(str).map(nome_normalizado)
    return numerico.fillna(texto.map(meses))


def data_oficial(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, errors="coerce", format="mixed", dayfirst=True)


def tempo_com_fallback(ano, mes, datas):
    anos = pd.to_numeric(ano, errors="coerce")
    meses = mes_numerico(mes)
    anos = anos.where(anos.between(1990, 2100), datas.dt.year)
    meses = meses.where(meses.between(1, 12), datas.dt.month)
    return anos, meses


def campo(df: pd.DataFrame, nome: str, padrao=None):
    return df[nome] if nome in df.columns else pd.Series([padrao] * len(df), index=df.index)


def transformar(conjunto: str, bruto: pd.DataFrame) -> pd.DataFrame:
    bruto.columns = [nome_normalizado(c) for c in bruto.columns]
    if conjunto == "empenhos":
        datas = data_oficial(campo(bruto, "DATA_EMPENHO"))
        exercicio = pd.to_numeric(campo(bruto, "NUMR_ANO"), errors="coerce")
        anos, meses = tempo_com_fallback(datas.dt.year, campo(bruto, "NUM_MES"), datas)
        saida = pd.DataFrame({
            "ano": anos, "mes": meses, "ano_exercicio": exercicio,
            "numero_empenho": campo(bruto, "NUMR_EMPENHO"), "numero_processo": campo(bruto, "NUMR_PROCESSO_EMPENHO"),
            "codigo_orgao": campo(bruto, "CODG_ORGAO"), "nome_orgao": campo(bruto, "NOME_ORGAO"), "documento_credor": campo(bruto, "CPF_CNPJ"),
            "nome_credor": campo(bruto, "RAZAO_SOCIAL_CREDOR"), "data_empenho": datas,
            "dotacao": campo(bruto, "DOTACAO"), "descricao": campo(bruto, "DESCRICAO_EMPENHO"), "valor_empenhado": moeda(campo(bruto, "SALDO_EMPENHADO", 0)),
        })
    elif conjunto == "liquidacoes":
        datas = data_oficial(campo(bruto, "DATA_DA_LIQUIDACAO"))
        exercicio = pd.to_numeric(campo(bruto, "NUMR_ANO"), errors="coerce")
        anos, meses = tempo_com_fallback(datas.dt.year, datas.dt.month, datas)
        saida = pd.DataFrame({
            "ano": anos, "mes": meses, "ano_exercicio": exercicio,
            "codigo_liquidacao": campo(bruto, "CODG_LIQUIDACAO"), "numero_empenho": campo(bruto, "NUMR_EMPENHO"),
            "codigo_orgao": campo(bruto, "CODG_ORGAO"), "nome_orgao": campo(bruto, "NOME_ORGAO"), "documento_credor": campo(bruto, "CPF_CNPJ_CREDOR"),
            "nome_credor": campo(bruto, "NOME_CREDOR"), "data_liquidacao": datas,
            "descricao": campo(bruto, "DESCRICAO_LIQUIDACAO"), "valor_liquidado": moeda(campo(bruto, "SALDO_LIQUIDADO", 0)),
        })
    elif conjunto == "pagamentos":
        datas_pagamento = data_oficial(campo(bruto, "DATA_COMPLETA"))
        ano, meses = tempo_com_fallback(campo(bruto, "NUMR_ANO"), campo(bruto, "NUM_MES"), datas_pagamento)
        exercicio = pd.to_numeric(campo(bruto, "EXERCICIO"), errors="coerce")
        saida = pd.DataFrame({
            "ano": ano, "mes": meses, "ano_exercicio": exercicio,
            "numero_sequencial_op": campo(bruto, "NUMR_SEQUENCIAL_OP"), "numero_empenho": campo(bruto, "NUMR_EMPENHO"),
            "codigo_orgao": campo(bruto, "CODG_ORGAO"), "nome_orgao": campo(bruto, "NOME_ORGAO"), "documento_credor": campo(bruto, "CPF_CNPJ_CREDOR"),
            "nome_credor": campo(bruto, "NOME_CREDOR"), "data_pagamento": datas_pagamento,
            "dotacao": campo(bruto, "DOTACAO"), "descricao": campo(bruto, "DESCRICAO"), "valor_pago": moeda(campo(bruto, "VALR_OP", 0)),
        })
    else:
        ano_mes = campo(bruto, "ANO_MES").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        ano_receita = pd.to_numeric(ano_mes.str[:4], errors="coerce").fillna(pd.to_numeric(campo(bruto, "ANO"), errors="coerce"))
        mes_receita = pd.to_numeric(ano_mes.str[4:6], errors="coerce").fillna(mes_numerico(campo(bruto, "MES")))
        saida = pd.DataFrame({
            "ano": ano_receita, "mes": mes_receita,
            "codigo_orgao": campo(bruto, "CODG_ORGAO"), "nome_orgao": campo(bruto, "NOME_ORGAO"), "categoria_economica": campo(bruto, "CATEGORIA_ECONOMICA"),
            "origem": campo(bruto, "ORIGEM"), "especie": campo(bruto, "ESPECIE"), "rubrica": campo(bruto, "RUBRICA"), "alinea": campo(bruto, "ALINEA"),
            "subalinea": campo(bruto, "SUBALINEA"), "codigo_natureza": campo(bruto, "CODG_NATUREZA_RECEITA"),
            "valor_previsto": moeda(campo(bruto, "RECEITA_PREVISTA_LOA", 0)), "valor_realizado": moeda(campo(bruto, "RECEITA_REALIZADA", 0)),
        })
    saida["ano"] = saida["ano"].fillna(0).astype(int)
    saida["mes"] = saida["mes"].fillna(0).astype(int)
    return saida.where(pd.notna(saida), None)


def detectar_codificacao(amostra: bytes) -> tuple[str, str]:
    """Prefere UTF-8 mesmo quando alguns poucos bytes da amostra são inválidos —
    um arquivo majoritariamente UTF-8 com uma única linha corrompida não deve ser
    lido inteiro como Latin-1, o que transformaria todo acento correto em mojibake
    (ex.: 'agência' -> 'agÃªncia'). Só recai para Latin-1 quando a taxa de bytes
    inválidos indica que o arquivo é de fato Latin-1."""
    try:
        return "utf-8-sig", amostra.decode("utf-8-sig").splitlines()[0]
    except UnicodeDecodeError:
        pass
    decodificado = amostra.decode("utf-8", errors="replace")
    taxa_erro = decodificado.count("�") / max(len(decodificado), 1)
    if taxa_erro < 0.001:
        return "utf-8", decodificado.splitlines()[0]
    return "latin1", amostra.decode("latin1").splitlines()[0]


def chave_conteudo(df: pd.DataFrame) -> pd.Series:
    textos = df.astype(str).agg("\x1f".join, axis=1)
    return textos.map(lambda valor: hashlib.sha256(valor.encode("utf-8")).hexdigest())


def catalogo(nome: str) -> list[dict]:
    resposta = requests.get(f"https://dadosabertos.go.gov.br/api/3/action/package_show?id={CATALOGOS[nome]}", timeout=60)
    resposta.raise_for_status()
    return resposta.json()["result"]["resources"]


def baixar(recurso: dict, destino: Path) -> tuple[str, int]:
    resumo = hashlib.sha256()
    total = 0
    with requests.get(recurso["url"], stream=True, timeout=180) as resposta:
        resposta.raise_for_status()
        with destino.open("wb") as arquivo:
            for bloco in resposta.iter_content(1024 * 1024):
                if bloco:
                    arquivo.write(bloco); resumo.update(bloco); total += len(bloco)
    return resumo.hexdigest(), total


def iterar_csvs(caminho: Path, formato: str):
    if formato == "ZIP":
        with zipfile.ZipFile(caminho) as arquivo_zip:
            for nome in arquivo_zip.namelist():
                if nome.upper().endswith(".CSV") and "__MACOSX" not in nome.upper() and not Path(nome).name.startswith("._"):
                    with arquivo_zip.open(nome) as arquivo:
                        yield arquivo
    else:
        with caminho.open("rb") as arquivo:
            yield arquivo


def carregar_recurso(versao_id: int, conjunto: str, recurso: dict) -> int:
    formato = recurso["format"].upper()
    with tempfile.TemporaryDirectory(prefix="radar_carga_") as diretorio:
        caminho = Path(diretorio) / f"recurso.{formato.lower()}"
        sha256, tamanho = baixar(recurso, caminho)
        with engine.begin() as conexao:
            recurso_id = conexao.execute(text("""
                INSERT INTO recursos_ingestao
                    (versao_id, conjunto, recurso_ckan_id, nome, url, formato, modificado_em, sha256, bytes_baixados, registros)
                VALUES (:versao, :conjunto, :id, :nome, :url, :formato, :modificado, :sha, :bytes, 0)
                RETURNING id
            """), {"versao": versao_id, "conjunto": conjunto, "id": recurso["id"], "nome": recurso["name"], "url": recurso["url"],
                    "formato": formato, "modificado": recurso.get("last_modified"), "sha": sha256, "bytes": tamanho}).scalar_one()

        total = 0
        for arquivo in iterar_csvs(caminho, formato):
            amostra = arquivo.read(65_536)
            codificacao, primeira = detectar_codificacao(amostra)
            separador = ";" if primeira.count(";") > primeira.count(",") else ","
            arquivo.seek(0)
            for bruto in pd.read_csv(
                arquivo, sep=separador, encoding=codificacao, encoding_errors="replace",
                dtype=str, on_bad_lines="error", chunksize=50_000,
            ):
                dados = transformar(conjunto, bruto)
                dados.insert(0, "linha_origem", range(total + 1, total + len(dados) + 1))
                dados.insert(0, "recurso_id", recurso_id)
                dados.insert(0, "versao_id", versao_id)
                colunas_hash = [c for c in dados.columns if c not in {"versao_id", "recurso_id", "linha_origem"}]
                dados["chave_conteudo"] = chave_conteudo(dados[colunas_hash])
                dados.to_sql(TABELAS[conjunto], engine, if_exists="append", index=False, chunksize=5_000)
                total += len(dados)
        with engine.begin() as conexao:
            conexao.execute(text("UPDATE recursos_ingestao SET registros=:total WHERE id=:id"), {"total": total, "id": recurso_id})
        return total


def validar_versao(versao_id: int, conjuntos: list[str], ano_esperado: int | None = None) -> dict:
    metricas = {}
    with engine.connect() as conexao:
        for conjunto in conjuntos:
            tabela = TABELAS[conjunto]
            coluna_valor = {"empenhos": "valor_empenhado", "liquidacoes": "valor_liquidado", "pagamentos": "valor_pago", "receitas": "valor_realizado"}[conjunto]
            coluna_exercicio = "ano_exercicio" if conjunto != "receitas" else "ano"
            linha = conexao.execute(text(f"""
                SELECT COUNT(*) registros, MIN(ano) ano_min, MAX(ano) ano_max,
                       MIN({coluna_exercicio}) ano_exercicio_min, MAX({coluna_exercicio}) ano_exercicio_max,
                       COUNT(*) FILTER (WHERE mes NOT BETWEEN 1 AND 12) meses_invalidos,
                       COUNT(*) FILTER (WHERE ano NOT BETWEEN 1990 AND EXTRACT(YEAR FROM CURRENT_DATE)::int) anos_invalidos,
                       SUM(ABS({coluna_valor})) soma_absoluta
                FROM {tabela} WHERE versao_id=:versao
            """), {"versao": versao_id}).mappings().one()
            sobreposicoes = conexao.execute(text(f"""
                SELECT COUNT(*) FROM (SELECT chave_conteudo FROM {tabela} WHERE versao_id=:versao
                GROUP BY chave_conteudo HAVING COUNT(DISTINCT recurso_id) > 1) x
            """), {"versao": versao_id}).scalar_one()
            metricas[conjunto] = {**dict(linha), "conteudos_entre_recursos": sobreposicoes}
            ano_divergente = ano_esperado is not None and conjunto != "receitas" and (
                linha["ano_exercicio_min"] != ano_esperado or linha["ano_exercicio_max"] != ano_esperado
            )
            if ano_esperado is not None and conjunto == "receitas":
                ano_divergente = linha["ano_min"] != ano_esperado or linha["ano_max"] != ano_esperado
            if not linha["registros"] or linha["meses_invalidos"] or linha["anos_invalidos"] or not linha["soma_absoluta"] or sobreposicoes or ano_divergente:
                raise ValueError(f"Validação bloqueante falhou para {conjunto}: {metricas[conjunto]}")
    return metricas


def executar(conjuntos: list[str], ano: int | None) -> int:
    with engine.begin() as conexao:
        versao_id = conexao.execute(text("INSERT INTO versoes_dados (status, observacao) VALUES ('preparando', :obs) RETURNING id"),
                                    {"obs": f"Carga oficial isolada; ano={ano or 'todos'}"}).scalar_one()
    try:
        for conjunto in conjuntos:
            recursos = selecionar_recursos(catalogo(conjunto), ano)
            if not recursos:
                raise ValueError(f"Nenhum recurso independente encontrado para {conjunto}.")
            for recurso in recursos:
                print(f"[{conjunto}] {recurso['name']}", flush=True)
                print(f"  {carregar_recurso(versao_id, conjunto, recurso):,} registros", flush=True)
        metricas = validar_versao(versao_id, conjuntos, ano)
        with engine.begin() as conexao:
            conexao.execute(text("UPDATE versoes_dados SET status='validada', finalizado_em=now(), metricas=CAST(:metricas AS jsonb) WHERE id=:id"),
                            {"id": versao_id, "metricas": json.dumps(metricas, default=str)})
        print(f"Versão {versao_id} validada e ainda não ativada.")
        return versao_id
    except Exception as erro:
        with engine.begin() as conexao:
            conexao.execute(text("UPDATE versoes_dados SET status='rejeitada', finalizado_em=now(), observacao=:erro WHERE id=:id"),
                            {"id": versao_id, "erro": str(erro)[:4000]})
        raise


def main():
    parser = argparse.ArgumentParser(description="Carga financeira oficial, versionada e não destrutiva.")
    parser.add_argument("--conjuntos", nargs="+", choices=tuple(CATALOGOS), default=list(CATALOGOS))
    parser.add_argument("--ano", type=int)
    args = parser.parse_args()
    executar(args.conjuntos, args.ano)


if __name__ == "__main__":
    main()
