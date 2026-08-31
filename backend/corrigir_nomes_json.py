import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PASTAS = (
    BASE_DIR / "dados_gerados",
    BASE_DIR.parent / "frontend" / "radar-front" / "public" / "dados",
)
MARCADORES = ("Ã", "Â", "â", "ð", "�", "\x80", "\x81", "\x82", "\x83", "\x84", "\x85", "\x86", "\x87", "\x88", "\x89", "\x8a", "\x8b", "\x8c", "\x8d", "\x8e", "\x8f", "\x90", "\x91", "\x92", "\x93", "\x94", "\x95", "\x96", "\x97", "\x98", "\x99")
CONECTIVOS = {"de", "da", "do", "das", "dos", "e", "em", "a", "o", "com", "para"}
SUFIXOS = {"ltda", "me", "epp", "eireli", "sa", "s/a", "s.a", "s.a."}
CHAVES_NOME = {"name", "nome", "orgao", "nome_orgao", "nome_servidor", "nome_contratado", "nome_credor"}


def corrigir_mojibake(texto: str) -> str:
    corrigido = texto
    for _ in range(2):
        if not any(marcador in corrigido for marcador in MARCADORES):
            break
        candidato = None
        for codificacao in ("cp1252", "latin1"):
            try:
                candidato = corrigido.encode(codificacao).decode("utf-8")
                break
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        if candidato is None:
            break
        if candidato == corrigido:
            break
        corrigido = candidato
    return corrigido


def formatar_nome_proprio(texto: str) -> str:
    normalizado = texto.strip()
    if not normalizado:
        return normalizado
    tudo_maiusculo = normalizado == normalizado.upper() and normalizado != normalizado.lower()
    tudo_minusculo = normalizado == normalizado.lower()
    if not tudo_maiusculo and not tudo_minusculo:
        return normalizado
    palavras = []
    for indice, palavra in enumerate(normalizado.lower().split(" ")):
        base = palavra.strip(".,")
        if base in SUFIXOS:
            palavras.append(palavra.upper())
        elif indice > 0 and palavra in CONECTIVOS:
            palavras.append(palavra)
        else:
            palavras.append(palavra[:1].upper() + palavra[1:])
    formatado = " ".join(palavras)
    partes = formatado.split(" - ")
    if len(partes) > 1 and len(partes[-1]) <= 15 and " " not in partes[-1]:
        partes[-1] = partes[-1].upper()
    return " - ".join(partes)


def corrigir_valor(valor, chave_atual: str | None = None):
    if isinstance(valor, str):
        texto = corrigir_mojibake(valor)
        return formatar_nome_proprio(texto) if chave_atual in CHAVES_NOME else texto
    if isinstance(valor, list):
        return [corrigir_valor(item, chave_atual) for item in valor]
    if isinstance(valor, dict):
        return {
            corrigir_mojibake(str(chave)): corrigir_valor(item, str(chave).lower())
            for chave, item in valor.items()
        }
    return valor


def corrigir_arquivo(caminho: Path) -> int:
    with caminho.open(encoding="utf-8") as arquivo:
        original = json.load(arquivo)
    corrigido = corrigir_valor(original)
    if corrigido == original:
        return 0

    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    with temporario.open("w", encoding="utf-8", newline="\n") as arquivo:
        json.dump(corrigido, arquivo, ensure_ascii=False, indent=4)
        arquivo.write("\n")
    os.replace(temporario, caminho)
    return 1


def atualizar_nomes_json() -> tuple[int, int]:
    analisados = 0
    alterados = 0
    for pasta in PASTAS:
        for caminho in sorted(pasta.glob("cache_*.json")):
            analisados += 1
            alterados += corrigir_arquivo(caminho)
    print(f"JSON analisados: {analisados}; arquivos alterados: {alterados}.")
    return analisados, alterados


if __name__ == "__main__":
    atualizar_nomes_json()
