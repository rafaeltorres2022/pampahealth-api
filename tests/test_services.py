import unittest
from datetime import date

from api import services


def caso(doenca_id=1, doenca="Raiva", local_id=1, pais="Brasil", cidade="Santiago",
         data=date(2026, 3, 10), oa=0, oh=0, ma=0, mh=0):
    return {
        "doenca_id": doenca_id, "doenca": doenca, "local_id": local_id,
        "pais": pais, "cidade": cidade, "data": data,
        "ocorrencias_animal": oa, "ocorrencias_humano": oh,
        "mortes_animal": ma, "mortes_humano": mh,
    }


class SummarizeTests(unittest.TestCase):
    def test_soma_animal_e_humano(self):
        r = services.summarize([caso(oa=3, oh=2, ma=1, mh=1), caso(oa=1)])
        self.assertEqual(r["ocorrencias"], 6)
        self.assertEqual(r["ocorrencias_animal"], 4)
        self.assertEqual(r["ocorrencias_humano"], 2)
        self.assertEqual(r["mortes"], 2)

    def test_vazio(self):
        self.assertEqual(services.summarize([])["ocorrencias"], 0)


class AgrupamentoTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            caso(1, "Raiva", 1, "Brasil", "Santiago", oa=5, ma=2),
            caso(1, "Raiva", 2, "Uruguai", "Rivera", oa=1),
            caso(2, "Leptospirose", 1, "Brasil", "Santiago", oh=10, mh=3),
        ]

    def test_por_doenca_ordenado_por_ocorrencias(self):
        r = services.by_disease(self.rows)
        self.assertEqual([d["doenca"] for d in r], ["Leptospirose", "Raiva"])
        self.assertEqual(r[1]["ocorrencias"], 6)
        self.assertEqual(r[1]["mortes"], 2)

    def test_bolhas_por_local_com_detalhe_por_doenca(self):
        r = services.map_bubbles(self.rows)
        self.assertEqual(len(r), 2)
        santiago = r[0]
        self.assertEqual(santiago["cidade"], "Santiago")
        self.assertEqual(santiago["ocorrencias"], 15)
        self.assertEqual(santiago["mortes"], 5)
        self.assertEqual({d["doenca"] for d in santiago["doencas"]}, {"Raiva", "Leptospirose"})


class PeriodoTests(unittest.TestCase):
    def test_periodo_anterior_tem_mesma_duracao(self):
        ini, fim = services.previous_period(date(2026, 3, 1), date(2026, 3, 10))
        self.assertEqual((ini, fim), (date(2026, 2, 19), date(2026, 2, 28)))

    def test_resolve_periodo_padrao_30_dias(self):
        ini, fim = services.resolve_period(None, None, hoje=date(2026, 3, 30))
        self.assertEqual((ini, fim), (date(2026, 3, 1), date(2026, 3, 30)))

    def test_resolve_mantem_valores_informados(self):
        ini, fim = services.resolve_period(date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual((ini, fim), (date(2026, 1, 1), date(2026, 1, 31)))


class VariacaoTests(unittest.TestCase):
    def test_crescimento(self):
        self.assertEqual(services.variation(15, 10)["variacao_percentual"], 50.0)

    def test_queda(self):
        v = services.variation(5, 10)
        self.assertEqual(v["variacao_absoluta"], -5)
        self.assertEqual(v["variacao_percentual"], -50.0)

    def test_sem_base_anterior(self):
        self.assertIsNone(services.variation(7, 0)["variacao_percentual"])

    def test_zero_e_zero(self):
        self.assertEqual(services.variation(0, 0)["variacao_percentual"], 0.0)


class CrescimentoTests(unittest.TestCase):
    def setUp(self):
        self.inicio, self.fim = date(2026, 3, 1), date(2026, 3, 31)  # 31 dias
        self.rows = [
            caso(1, "Raiva", data=date(2026, 3, 5), oa=15, ma=3),      # atual
            caso(1, "Raiva", data=date(2026, 2, 10), oa=10, ma=2),     # anterior
            caso(2, "Leptospirose", data=date(2026, 3, 20), oh=4),     # só atual
            caso(3, "Brucelose", data=date(2026, 2, 12), oh=6),        # só anterior
            caso(1, "Raiva", data=date(2025, 6, 1), oa=99),            # fora das janelas
            caso(1, "Raiva", data=None, oa=99),                        # sem data
        ]

    def test_totais(self):
        r = services.growth_report(self.rows, self.inicio, self.fim)
        self.assertEqual(r["total"]["ocorrencias"]["atual"], 19)
        self.assertEqual(r["total"]["ocorrencias"]["anterior"], 16)
        self.assertEqual(r["periodo"]["dias"], 31)
        self.assertEqual(r["periodo_anterior"]["inicio"], "2026-01-29")

    def test_por_doenca(self):
        r = services.growth_report(self.rows, self.inicio, self.fim)
        d = {x["doenca"]: x for x in r["doencas"]}
        self.assertEqual(d["Raiva"]["ocorrencias"]["variacao_percentual"], 50.0)
        self.assertEqual(d["Raiva"]["mortes"]["variacao_absoluta"], 1)
        self.assertIsNone(d["Leptospirose"]["ocorrencias"]["variacao_percentual"])
        self.assertEqual(d["Brucelose"]["ocorrencias"]["atual"], 0)
        self.assertEqual(d["Brucelose"]["ocorrencias"]["variacao_percentual"], -100.0)

    def test_serie_mensal_preenche_zeros(self):
        rows = [caso(data=date(2026, 1, 15), oa=2), caso(data=date(2026, 3, 2), oa=5)]
        s = services.time_series(rows, date(2026, 1, 1), date(2026, 3, 31), "mes")
        self.assertEqual(
            [(p["inicio"], p["ocorrencias"]) for p in s],
            [("2026-01-01", 2), ("2026-02-01", 0), ("2026-03-01", 5)],
        )

    def test_serie_semanal_comeca_na_segunda(self):
        s = services.time_series([], date(2026, 3, 4), date(2026, 3, 18), "semana")  # 4/mar = quarta
        self.assertEqual([p["inicio"] for p in s], ["2026-03-02", "2026-03-09", "2026-03-16"])

    def test_serie_diaria(self):
        s = services.time_series([], date(2026, 3, 1), date(2026, 3, 3), "dia")
        self.assertEqual(len(s), 3)

    def test_virada_de_ano_mensal(self):
        s = services.time_series([], date(2025, 11, 20), date(2026, 1, 5), "mes")
        self.assertEqual([p["inicio"] for p in s], ["2025-11-01", "2025-12-01", "2026-01-01"])


if __name__ == "__main__":
    unittest.main()
