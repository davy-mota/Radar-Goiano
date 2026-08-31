import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from database import engine  # noqa: E402


def _postgres_com_versao_ativa() -> bool:
    if not str(engine.url).startswith("postgresql"):
        return False
    try:
        with engine.connect() as conexao:
            return bool(conexao.execute(text(
                "SELECT 1 FROM versoes_dados WHERE status='ativa' LIMIT 1"
            )).scalar())
    except OperationalError:
        return False


POSTGRES_DISPONIVEL = _postgres_com_versao_ativa()


@unittest.skipUnless(
    POSTGRES_DISPONIVEL,
    "Requer PostgreSQL real (DATABASE_URL) com uma versão ativa em versoes_dados.",
)
class EndpointsMigradosTest(unittest.TestCase):
    """Testes de integração via TestClient contra o PostgreSQL real, cobrindo os
    endpoints migrados para a camada versionada (fatos_*/vw_*_ativos) no Incremento 8.
    Servem também como teste de regressão para os dois bugs pré-existentes que a
    migração corrigiu: empenhado/liquidado sempre zerados e função sempre vazia."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from main import app

        cls.cliente = TestClient(app)

    def test_filtros_despesas_nao_tem_mais_funcao(self):
        resposta = self.cliente.get("/api/despesas/filtros", params={"ano": "2025"})
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertNotIn("funcoes", corpo)
        self.assertTrue(corpo["orgaos"])

    def test_resumo_despesas_empenhado_e_liquidado_nao_sao_mais_sempre_zero(self):
        resposta = self.cliente.get("/api/despesas/resumo", params={"ano": "2025"})
        self.assertEqual(resposta.status_code, 200)
        kpis = resposta.json()["kpis"]
        self.assertGreater(kpis["empenhado"], 0)
        self.assertGreater(kpis["liquidado"], 0)

    def test_listagem_despesas_nao_expoe_mais_valor_por_linha_de_empenho(self):
        resposta = self.cliente.get("/api/despesas", params={"ano": "2025", "por_pagina": 10})
        self.assertEqual(resposta.status_code, 200)
        itens = resposta.json()["itens"]
        self.assertTrue(itens)
        self.assertNotIn("valor_empenhado", itens[0])
        self.assertIn("valor_pago", itens[0])

    def test_alertas_regra_4_agrupa_por_orgao(self):
        resposta = self.cliente.get("/api/alertas", params={"ano": 2025, "tipo": "atipico_iqr"})
        self.assertEqual(resposta.status_code, 200)
        grupo = resposta.json()["grupos"][0]
        self.assertEqual(grupo["titulo"], "Pagamentos atípicos por órgão")
        if grupo["itens"]:
            self.assertNotIn("funcao", grupo["itens"][0])
            self.assertIn("orgao", grupo["itens"][0])

    def test_comparador_expoe_top_credores_nao_top_funcoes(self):
        with engine.connect() as conexao:
            orgao = conexao.execute(text("""
                SELECT normalizar_texto_utf8(nome_orgao) FROM vw_pagamentos_ativos
                WHERE ano_exercicio = 2025 GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1
            """)).scalar_one()
        resposta = self.cliente.get("/api/comparacoes/orgaos", params={
            "orgao_a": orgao, "ano_a": 2025, "orgao_b": orgao, "ano_b": 2025,
        })
        self.assertEqual(resposta.status_code, 200)
        cenario = resposta.json()["cenario_a"]
        self.assertIn("top_credores", cenario)
        self.assertNotIn("top_funcoes", cenario)

    def test_fiscal_resumo_empenhado_nao_zerado(self):
        resposta = self.cliente.get("/api/fiscal/resumo", params={"ano": 2025})
        self.assertEqual(resposta.status_code, 200)
        self.assertGreater(resposta.json()["despesa"]["empenhado"], 0)

    def test_fornecedor_resumo_responde_sem_erro(self):
        with engine.connect() as conexao:
            documento = conexao.execute(text("""
                SELECT documento_credor FROM vw_pagamentos_ativos
                WHERE documento_credor ~ '^[0-9.\\/-]+$' GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1
            """)).scalar_one()
        cnpj = "".join(c for c in documento if c.isdigit()).zfill(14)
        resposta = self.cliente.get(f"/api/fornecedores/{cnpj}/resumo")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("empenhado", resposta.json()["kpis"])

    def test_metadados_e_cargas_respondem(self):
        self.assertEqual(self.cliente.get("/api/metadados").status_code, 200)
        self.assertEqual(self.cliente.get("/api/cargas", params={"limite": 5}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
