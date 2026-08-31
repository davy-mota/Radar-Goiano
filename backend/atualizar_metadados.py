from sqlalchemy import text

from database import engine


if __name__ == "__main__":
    with engine.begin() as conexao:
        conexao.execute(text("SELECT atualizar_metadados_qualidade();"))
    print("Metadados de qualidade atualizados com sucesso.")
