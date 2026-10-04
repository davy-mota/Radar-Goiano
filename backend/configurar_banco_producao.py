import os

import psycopg2
from psycopg2 import sql


def obrigatoria(nome):
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável obrigatória ausente: {nome}")
    return valor


def configurar():
    banco = obrigatoria("DB_NAME")
    usuario_api = obrigatoria("API_DB_USER")
    senha_api = obrigatoria("API_DB_PASSWORD")
    conexao = psycopg2.connect(
        host=obrigatoria("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=banco,
        user=obrigatoria("DB_ADMIN_USER"),
        password=obrigatoria("DB_ADMIN_PASSWORD"),
    )
    conexao.autocommit = True
    with conexao.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (usuario_api,))
        if cursor.fetchone() is None:
            cursor.execute(
                sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(usuario_api))
            )
        cursor.execute(
            sql.SQL("ALTER ROLE {} PASSWORD %s").format(sql.Identifier(usuario_api)),
            (senha_api,),
        )
        cursor.execute(
            sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(
                sql.Identifier(usuario_api)
            )
        )
        cursor.execute(
            sql.SQL("ALTER ROLE {} SET statement_timeout = '30s'").format(
                sql.Identifier(usuario_api)
            )
        )
        cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(banco), sql.Identifier(usuario_api)
        ))
        cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
            sql.Identifier(usuario_api)
        ))
        cursor.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(
            sql.Identifier(usuario_api)
        ))
        cursor.execute(sql.SQL("GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(
            sql.Identifier(usuario_api)
        ))
        cursor.execute(sql.SQL(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}"
        ).format(sql.Identifier(usuario_api)))
        cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    conexao.close()
    print(f"Usuário {usuario_api} configurado com acesso somente leitura.")


if __name__ == "__main__":
    configurar()
