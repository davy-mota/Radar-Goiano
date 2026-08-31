import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from controllers.rotas_despesas import (  # noqa: E402
    _celula_csv,
    _documento_para_exportacao,
    _filtros_sql,
    _validar_ano,
)
from controllers.rotas_fornecedores import validar_cnpj  # noqa: E402
from controllers.rotas_comparacoes import validar_cenario, variacao_percentual  # noqa: E402
from controllers.sql_utils import ORGAO_NORMALIZADO  # noqa: E402
from controllers.rotas_fiscal import avaliar_previsao  # noqa: E402
from controllers.rotas_alertas import percentual_variacao  # noqa: E402
from executar_carga import validar_conjunto  # noqa: E402
from carga_financeira_versionada import data_oficial, mes_numerico, nome_normalizado, selecionar_recursos  # noqa: E402
from corrigir_nomes_json import corrigir_mojibake, formatar_nome_proprio  # noqa: E402
import pandas as pd  # noqa: E402
from fastapi import HTTPException  # noqa: E402


class FiltrosDespesasTest(unittest.TestCase):
    def test_ano_valido(self):
        self.assertEqual(_validar_ano("2025"), "2025")
        self.assertEqual(_validar_ano("todos"), "todos")

    def test_ano_invalido(self):
        with self.assertRaises(HTTPException):
            _validar_ano("2025 OR 1=1")

    def test_filtros_usam_parametros_vinculados(self):
        where, parametros = _filtros_sql(
            "2025", mes=4, orgao="Secretaria", busca="empresa"
        )
        self.assertIn("ano_exercicio = :ano", where)
        self.assertIn(f"{ORGAO_NORMALIZADO} = :orgao", where)
        self.assertNotIn("Secretaria", where)
        self.assertEqual(parametros["busca"], "%empresa%")

    def test_csv_neutraliza_formula(self):
        self.assertEqual(_celula_csv("=1+1"), "'=1+1")
        self.assertEqual(_celula_csv("texto\nquebrado"), "texto quebrado")

    def test_exportacao_mascara_cpf(self):
        self.assertEqual(_documento_para_exportacao("123.456.789-00"), "***.***.***-**")
        self.assertEqual(_documento_para_exportacao("11.991.625/0001-89"), "11991625000189")


class HistoricoCargasTest(unittest.TestCase):
    def test_conjunto_valido_usa_lista_fechada(self):
        self.assertEqual(validar_conjunto("pagamentos")["script"], "extracao_de_gastos.py")

    def test_conjunto_desconhecido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            validar_conjunto("script_arbitrario")

    def test_cargas_legadas_com_append_ficam_bloqueadas(self):
        self.assertFalse(validar_conjunto("pagamentos")["habilitado"])
        self.assertFalse(validar_conjunto("receitas")["habilitado"])


class CargaVersionadaTest(unittest.TestCase):
    def test_normaliza_cabecalho_oficial(self):
        self.assertEqual(nome_normalizado("Liquidações / mês"), "LIQUIDACOES_MES")

    def test_selecao_exclui_consolidado_e_sobreposicao(self):
        recursos = [
            {"name": "Pagamentos - 2024", "format": "ZIP"},
            {"name": "Pagamentos 2003 - 2024", "format": "ZIP"},
            {"name": "Pagamentos - Janeiro/2025", "format": "CSV"},
        ]
        nomes = [r["name"] for r in selecionar_recursos(recursos)]
        self.assertEqual(nomes, ["Pagamentos - 2024", "Pagamentos - Janeiro/2025"])

    def test_mes_por_extenso(self):
        self.assertEqual(mes_numerico(pd.Series(["Março", "11"])).tolist(), [3.0, 11.0])

    def test_datas_iso_e_brasileira(self):
        datas = data_oficial(pd.Series(["2024-03-12", "12/03/2024"]))
        self.assertEqual([(d.year, d.month, d.day) for d in datas], [(2024, 3, 12), (2024, 3, 12)])

    def test_corrige_mojibake_sem_alterar_texto_correto(self):
        self.assertEqual(corrigir_mojibake("Secretaria da Educação"), "Secretaria da Educação")
        self.assertEqual(corrigir_mojibake("Secretaria da EducaÃ§Ã£o"), "Secretaria da Educação")

    def test_formata_nome_preservando_conectivos_e_sigla(self):
        self.assertEqual(formatar_nome_proprio("SECRETARIA DE ESTADO - SEAD"), "Secretaria de Estado - SEAD")
        self.assertEqual(formatar_nome_proprio("SANEAMENTO DE GOIAS S/A"), "Saneamento de Goias S/A")


class FornecedorTest(unittest.TestCase):
    def test_cnpj_valido(self):
        self.assertEqual(validar_cnpj("11.991.625/0001-89"), "11991625000189")

    def test_cnpj_invalido(self):
        with self.assertRaises(HTTPException):
            validar_cnpj("11.111.111/1111-11")

    def test_texto_nao_e_aceito_como_documento(self):
        with self.assertRaises(HTTPException):
            validar_cnpj("11991625000189 OR 1=1")


class ComparacaoTest(unittest.TestCase):
    def test_variacao_percentual(self):
        self.assertEqual(variacao_percentual(100, 125), 25)
        self.assertEqual(variacao_percentual(100, 75), -25)
        self.assertIsNone(variacao_percentual(0, 10))

    def test_cenario_valido(self):
        self.assertEqual(validar_cenario(" Secretaria da Saúde ", 2025), ("Secretaria da Saúde", 2025))

    def test_cenario_invalido(self):
        with self.assertRaises(HTTPException):
            validar_cenario("", 2025)


class FiscalTest(unittest.TestCase):
    def test_previsao_com_cobertura_suficiente(self):
        resultado = avaliar_previsao(1_000, 100, 70)
        self.assertTrue(resultado["confiavel_para_percentual"])
        self.assertEqual(resultado["cobertura_percentual"], 70)

    def test_previsao_com_baixa_cobertura(self):
        resultado = avaliar_previsao(1_000, 100, 69)
        self.assertFalse(resultado["confiavel_para_percentual"])

    def test_previsao_sem_registros(self):
        resultado = avaliar_previsao(0, 0, 0)
        self.assertEqual(resultado["cobertura_percentual"], 0)


class AlertasTest(unittest.TestCase):
    def test_variacao_de_alerta(self):
        self.assertEqual(percentual_variacao(100, 300), 200)
        self.assertEqual(percentual_variacao(100, 50), -50)
        self.assertIsNone(percentual_variacao(0, 100))


if __name__ == "__main__":
    unittest.main()
