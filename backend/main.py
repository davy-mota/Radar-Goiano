import os

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from dotenv import load_dotenv
from sqlalchemy import text

from database import engine

# Importando TODAS as rotas da pasta controllers
from controllers import (
    rotas_alertas,
    rotas_cargas,
    rotas_contratos,
    rotas_comparacoes,
    rotas_despesas,
    rotas_diarias,
    rotas_emendas,
    rotas_folha,
    rotas_fiscal,
    rotas_fornecedores,
    rotas_gerais,
    rotas_governador,
    rotas_parlamentares,
    rotas_metadados,
    rotas_politicas,
    rotas_repasses,
)

load_dotenv()
ambiente = os.getenv("ENVIRONMENT", "development").lower()
app = FastAPI(
    title="API Radar Goiano",
    version="1.0",
    docs_url=None if ambiente == "production" else "/docs",
    redoc_url=None if ambiente == "production" else "/redoc",
    openapi_url=None if ambiente == "production" else "/openapi.json",
)

origens_permitidas = [
    origem.strip()
    for origem in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origem.strip()
]
hosts_permitidos = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts_permitidos)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configuração para permitir que o React converse com o Python
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_permitidas,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def seguranca_http(request: Request, call_next):
    tamanho = request.headers.get("content-length")
    if tamanho:
        try:
            if int(tamanho) > 1_048_576:
                return JSONResponse(status_code=413, content={"detail": "Requisição muito grande."})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Content-Length inválido."})
    resposta = await call_next(request)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resposta.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    resposta.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )
    if ambiente == "production":
        resposta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resposta.headers["Cache-Control"] = "no-store" if request.url.path == "/health" else "public, max-age=60"
    return resposta

# Registrando TODAS as rotas no sistema (Avisando o Garçom)
app.include_router(rotas_contratos.router)
app.include_router(rotas_folha.router)
app.include_router(rotas_diarias.router)
app.include_router(rotas_gerais.router) # <-- O SEGREDO ESTÁ AQUI
app.include_router(rotas_despesas.router)
app.include_router(rotas_fornecedores.router)
app.include_router(rotas_comparacoes.router)
app.include_router(rotas_fiscal.router)
app.include_router(rotas_alertas.router)
app.include_router(rotas_metadados.router)
app.include_router(rotas_cargas.router)
app.include_router(rotas_politicas.router)
app.include_router(rotas_repasses.router)
app.include_router(rotas_emendas.router)
app.include_router(rotas_parlamentares.router)
app.include_router(rotas_governador.router)

@app.get("/")
def read_root():
    return {"mensagem": "API Radar Goiano online"}


@app.get("/health", tags=["Infraestrutura"])
def health():
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        return {"status": "ok", "api": "online", "banco": "online"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "indisponivel", "api": "online", "banco": "offline"},
        )
