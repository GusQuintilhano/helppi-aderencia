"""Consulta a camada semântica pela linha de comando (sem LLM).

uv run python -m semantic.consulta taxa_aderencia gbv --cliente "Rede Alfa" --periodo "semana passada"
"""

import argparse
import json

from semantic import engine

p = argparse.ArgumentParser()
p.add_argument("metricas", nargs="+")
p.add_argument("--cliente")
p.add_argument("--cidade")
p.add_argument("--periodo", default="tudo")
p.add_argument("--agrupar-por", nargs="*", default=[])
p.add_argument("--sql", action="store_true", help="mostra o SQL gerado")
a = p.parse_args()

filtros = {k: v for k, v in {"cliente": a.cliente, "cidade": a.cidade}.items() if v}
r = engine.consultar(a.metricas, filtros, a.periodo, a.agrupar_por)
sql = r.pop("sql")
print(json.dumps(r, ensure_ascii=False, indent=2))
if a.sql:
    print(sql)
