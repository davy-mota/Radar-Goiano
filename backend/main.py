import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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

app = FastAPI(title="API Radar Goiano", version="1.0")

load_dotenv()
origens_permitidas = [
    origem.strip()
    for origem in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origem.strip()
]

# Configuração para permitir que o React converse com o Python
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_permitidas,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"mensagem": "API 100% Online e operando as 4 abas!"}
