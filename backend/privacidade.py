import re


CONECTIVOS_NOME = {"DA", "DAS", "DE", "DO", "DOS", "E"}
NOMES_AUSENTES = {"", "N/A", "NAO INFORMADO", "NÃO INFORMADO"}
CARGOS_PUBLICOS = ("GOVERNADOR", "DEPUTADO", "SENADOR")


def cargo_de_alta_exposicao(cargo: str | None) -> bool:
    texto = str(cargo or "").upper()
    return any(cargo_publico in texto for cargo_publico in CARGOS_PUBLICOS)


def anonimizar_nome_pessoa(nome: str | None) -> str:
    """Preserva o primeiro nome e reduz os demais a inicial + asteriscos."""
    texto = re.sub(r"\s+", " ", str(nome or "").strip())
    if texto.upper() in NOMES_AUSENTES:
        return texto or "Não informado"
    if "*" in texto:
        return texto

    partes = texto.split(" ")
    if len(partes) == 1:
        return f"{partes[0][0]}***"

    resultado = [partes[0]]
    for parte in partes[1:]:
        if parte.upper() in CONECTIVOS_NOME:
            resultado.append(parte.lower())
        else:
            resultado.append(f"{parte[0]}***")
    return " ".join(resultado)


def nome_pessoa_para_exibicao(
    nome: str | None,
    cargo: str | None = None,
    figura_publica: bool = False,
) -> str:
    if figura_publica or cargo_de_alta_exposicao(cargo):
        return str(nome or "Não informado")
    return anonimizar_nome_pessoa(nome)
