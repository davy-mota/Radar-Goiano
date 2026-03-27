from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter()

@router.get("/api/contratos/resumo")
def get_resumo_contratos(ano: str = "todos"):
    print(f"\n👉 [TESTE DE VIDA] O navegador pediu os dados do ano: {ano}")
    
    caminho = Path(__file__).parent.parent / f"cache_contratos_{ano}.json"
    print(f"📂 [TESTE DE CAMINHO] O Python está procurando o arquivo em: {caminho}")
    
    try:
        with open(caminho, 'r', encoding='utf-8') as f: 
            dados = json.load(f)
            print("✅ [SUCESSO] Arquivo lido e enviado para o navegador!")
            return dados
    except Exception as e: 
        print(f"❌ [ERRO] Falha ao tentar ler o arquivo: {str(e)}")
        return {"erro": f"Dados de Contratos para '{ano}' ainda não foram gerados."}