from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importando TODAS as rotas da pasta controllers
from controllers import rotas_contratos, rotas_folha, rotas_diarias, rotas_gerais

app = FastAPI(title="API Radar Goiano", version="1.0")

# Configuração para permitir que o React converse com o Python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrando TODAS as rotas no sistema (Avisando o Garçom)
app.include_router(rotas_contratos.router)
app.include_router(rotas_folha.router)
app.include_router(rotas_diarias.router)
app.include_router(rotas_gerais.router) # <-- O SEGREDO ESTÁ AQUI

@app.get("/")
def read_root():
    return {"mensagem": "API 100% Online e operando as 4 abas!"}