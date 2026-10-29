"""Garante que o agente (camada semântica) e o dashboard (mart) dão o MESMO número.

Se alguém mudar a definição em um lugar só, este teste quebra o build.
"""

import duckdb
import pytest

from semantic import engine


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(engine.BANCO), read_only=True)
    yield c
    c.close()


def test_paridade_cliente_semana(con):
    mart = con.execute(
        "select cliente_id, semana_inicio, taxa_aderencia, gbv, vagas_demandadas, vagas_atendidas "
        "from mart_aderencia_gbv_cliente_semana"
    ).fetchall()
    sem = engine.consultar(
        ["taxa_aderencia", "gbv", "vagas_demandadas", "vagas_atendidas"],
        agrupar_por=["cliente", "semana"], conexao=con,
    )
    agente = {(l["cliente"], l["semana"]): l for l in sem["linhas"]}
    assert len(agente) == len(mart) == 30
    for cliente, semana, taxa, gbv, dem, atd in mart:
        l = agente[(cliente, semana.isoformat())]
        assert l["vagas_demandadas"] == dem and l["vagas_atendidas"] == atd
        assert round(l["taxa_aderencia"], 4) == pytest.approx(taxa)
        assert l["gbv"] == pytest.approx(float(gbv))


# Perguntas de referência: a pergunta como o usuário faria, e o número do dashboard.
PERGUNTAS = [
    ("Rede Alfa", "semana passada", 52, 61),         # C01, semana de 05/10
    ("farmacias gama", "2026-09-21", 59, 70),        # C03, semana de 21/09
    ("Atacado Beta", "tudo", 173, 227),
    ("Épsilon", "2026-09-21..2026-09-27", 45, 62),   # C05, pior semana
]


@pytest.mark.parametrize("cliente,periodo,atendidas,demandadas", PERGUNTAS)
def test_perguntas_de_referencia(con, cliente, periodo, atendidas, demandadas):
    r = engine.consultar(
        ["vagas_atendidas", "vagas_demandadas", "taxa_aderencia"],
        {"cliente": cliente}, periodo, conexao=con,
    )
    linha = r["linhas"][0]
    assert (linha["vagas_atendidas"], linha["vagas_demandadas"]) == (atendidas, demandadas)
    assert linha["taxa_aderencia"] == pytest.approx(atendidas / demandadas)


def test_total_oficial(con):
    linha = engine.consultar(["taxa_aderencia", "gbv"], conexao=con)["linhas"][0]
    assert round(linha["taxa_aderencia"], 3) == 0.850
    assert linha["gbv"] == pytest.approx(244105.0)


def test_cliente_desconhecido_falha_explicitamente(con):
    with pytest.raises(ValueError, match="não reconhecido"):
        engine.consultar(["taxa_aderencia"], {"cliente": "Loja Inexistente"}, conexao=con)
