# Algumas linhas armazenam bytes UTF-8 interpretados como Latin-1. A presença de
# caracteres de controle identifica essas linhas; as demais permanecem intactas.
ORGAO_NORMALIZADO = "normalizar_texto_utf8(nome_orgao)"
CREDOR_NORMALIZADO = "normalizar_texto_utf8(nome_credor)"

# Nas tabelas fatos_*, documento_credor é gravado com a pontuação original da fonte
# (ex.: "01.409.705/0001-20"), não em 14 dígitos. Esta expressão normaliza para
# comparação com o CNPJ já validado em Python (ver rotas_fornecedores.validar_cnpj).
DOCUMENTO_CREDOR_NORMALIZADO = """
CASE
    WHEN documento_credor ~ '^[0-9.\\/-]+$'
     AND length(regexp_replace(documento_credor, '[^0-9]', '', 'g')) BETWEEN 12 AND 14
    THEN lpad(regexp_replace(documento_credor, '[^0-9]', '', 'g'), 14, '0')
END
"""


def por_mes(linhas) -> dict[int, dict]:
    """Indexa linhas de uma consulta agregada por mês, para combinar com outras fontes."""
    return {linha["mes"]: dict(linha) for linha in linhas}


def serie_mensal_combinada(*fontes: dict[int, dict]) -> list[dict]:
    """Combina séries mensais de fatos independentes (empenhos, liquidações, pagamentos,
    receitas) em uma lista de 12 meses. Cada fonte é um dict {mes: linha}; nenhuma junção
    linha a linha é feita — os fatos permanecem agregados separadamente por mês."""
    linhas = []
    for mes in range(1, 13):
        linha = {"mes": mes}
        for fonte in fontes:
            linha.update({chave: valor for chave, valor in fonte.get(mes, {}).items() if chave != "mes"})
        linhas.append(linha)
    return linhas
