"""Testes das views (requer Django instalado).

Rodar com:
    APP_ENV=development SUPABASE_URL_DEV=http://x SUPABASE_KEY_DEV=x python manage.py test
"""

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from api import repository

CASO = {
    "doenca_id": 1,
    "doenca": "Raiva",
    "local_id": 1,
    "pais": "Brasil",
    "cidade": "Santiago",
    "data": date(2026, 3, 5),
    "ocorrencias_animal": 4,
    "ocorrencias_humano": 1,
    "mortes_animal": 1,
    "mortes_humano": 0,
}


class ReadOnlyTests(SimpleTestCase):
    def test_metodos_de_escrita_sao_rejeitados(self):
        for method in ("post", "put", "patch", "delete"):
            response = getattr(self.client, method)("/api/v1/mapa/")
            self.assertEqual(response.status_code, 405, method)

    def test_health(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class MapaTests(SimpleTestCase):
    @patch("api.views.repository.fetch_casos", return_value=[CASO])
    def test_mapa(self, fetch):
        response = self.client.get("/api/v1/mapa/?doenca=1,2&pais=Brasil")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"]["ocorrencias"], 5)
        self.assertEqual(body["locais"][0]["cidade"], "Santiago")
        filters = fetch.call_args.args[0]
        self.assertEqual(filters.doencas, (1, 2))
        self.assertEqual(filters.pais, "Brasil")

    def test_ids_invalidos(self):
        self.assertEqual(self.client.get("/api/v1/mapa/?doenca=abc").status_code, 400)

    def test_periodo_invertido(self):
        r = self.client.get("/api/v1/mapa/?data_inicio=2026-03-10&data_fim=2026-03-01")
        self.assertEqual(r.status_code, 400)


class CrescimentoTests(SimpleTestCase):
    @patch("api.views.repository.fetch_casos", return_value=[CASO])
    def test_consulta_cobre_periodo_atual_e_anterior(self, fetch):
        r = self.client.get(
            "/api/v1/estatisticas/crescimento/?data_inicio=2026-03-01&data_fim=2026-03-31"
        )
        self.assertEqual(r.status_code, 200)
        filters: repository.CasoFilters = fetch.call_args.args[0]
        self.assertEqual(filters.data_inicio, date(2026, 1, 29))
        self.assertEqual(filters.data_fim, date(2026, 3, 31))
        self.assertEqual(r.json()["total"]["ocorrencias"]["atual"], 5)

    def test_granularidade_invalida(self):
        self.assertEqual(
            self.client.get(
                "/api/v1/estatisticas/crescimento/?granularidade=ano"
            ).status_code,
            400,
        )


LINHA_FONTE = {
    "fonte_id": 7,
    "titulo": "Surto de raiva",
    "url": "https://ex.com/7",
    "resumo_pt": "resumo",
    "resumo_en": None,
    "resumo_es": None,
    "idioma_original": "Português",
    "data": date(2026, 3, 5),
    "doenca_id": 1,
    "doenca": "Raiva",
    "pais": "Brasil",
    "cidade": "Santiago",
}


class FontesTests(SimpleTestCase):
    @patch("api.views.repository.fetch_fontes", return_value=[LINHA_FONTE])
    def test_lista_fontes(self, fetch):
        r = self.client.get("/api/v1/fontes/?doenca=1&limite=10")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["total"], 1)
        item = body["resultados"][0]
        self.assertEqual(item["titulo"], "Surto de raiva")
        self.assertEqual(item["resumo"], "resumo")
        self.assertEqual(item["url"], "https://ex.com/7")
        self.assertEqual(fetch.call_args.args[0].doencas, (1,))

    @patch("api.views.repository.fetch_fontes", return_value=[])
    def test_fontes_de_uma_doenca_usa_o_id_da_rota(self, fetch):
        r = self.client.get("/api/v1/doencas/5/fontes/?doenca=99")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(fetch.call_args.args[0].doencas, (5,))

    def test_parametros_invalidos(self):
        self.assertEqual(self.client.get("/api/v1/fontes/?idioma=fr").status_code, 400)
        self.assertEqual(
            self.client.get("/api/v1/fontes/?limite=1000").status_code, 400
        )
        self.assertEqual(self.client.get("/api/v1/fontes/?pagina=0").status_code, 400)
