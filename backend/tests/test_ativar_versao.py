import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ativar_versao  # noqa: E402


class AtivacaoVersaoTest(unittest.TestCase):
    def test_normaliza_timestamp_de_datetime_e_iso(self):
        esperado = "2026-08-28T14:23:00"
        self.assertEqual(
            ativar_versao._normalizar_timestamp(datetime(2026, 8, 28, 14, 23)), esperado
        )
        self.assertEqual(
            ativar_versao._normalizar_timestamp("2026-08-28T14:23:00.000Z"), esperado
        )

    @patch.object(ativar_versao, "_trocar_versao_ativa")
    @patch.object(ativar_versao, "verificar_estabilidade_fonte")
    def test_ativacao_bloqueia_recurso_removido(self, estabilidade, trocar):
        estabilidade.return_value = {
            "recursos_verificados": 1,
            "divergencias": ["pagamentos/2025: recurso removido"],
            "avisos": [],
        }
        with self.assertRaisesRegex(ValueError, "Ativação bloqueada"):
            ativar_versao.ativar(12)
        trocar.assert_not_called()

    @patch.object(ativar_versao, "_trocar_versao_ativa", return_value=123)
    @patch.object(ativar_versao, "verificar_estabilidade_fonte")
    def test_ativacao_forcada_registra_metricas(self, estabilidade, trocar):
        metricas = {
            "recursos_verificados": 1,
            "divergencias": ["recurso removido"],
            "avisos": [],
        }
        estabilidade.return_value = metricas
        self.assertEqual(ativar_versao.ativar(12, ignorar_divergencias=True), 123)
        trocar.assert_called_once_with(
            12,
            "validada",
            {"estabilidade_fonte": metricas},
            "ativação da versão 12 via ativar_versao.py",
        )

    @patch.object(ativar_versao, "_trocar_versao_ativa", return_value=321)
    def test_reversao_exige_status_arquivada(self, trocar):
        self.assertEqual(ativar_versao.reverter(10), 321)
        trocar.assert_called_once_with(
            10,
            "arquivada",
            {},
            "reversão para a versão 10 via ativar_versao.py --reverter",
        )


if __name__ == "__main__":
    unittest.main()
