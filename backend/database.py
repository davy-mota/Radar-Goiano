import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL and os.getenv("DB_HOST"):
    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER", "radar"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "radar_goiano"),
    )
if not DATABASE_URL:
    raise RuntimeError(
        "A variável de ambiente DATABASE_URL não foi definida. "
        "Copie .env.example para .env e informe a conexão do PostgreSQL."
    )

tempo_consulta_ms = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "5")),
    connect_args={
        "options": (
            f"-c statement_timeout={tempo_consulta_ms} "
            "-c idle_in_transaction_session_timeout=10000"
        )
    },
)
