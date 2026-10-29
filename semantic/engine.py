"""Motor da camada semântica: transforma um pedido de métrica em SQL sobre o fato.

Nenhum consumidor (agente, script, teste) escreve SQL de métrica à mão: todos
passam por `consultar`, que monta a consulta a partir de semantic/metricas.yml.
"""

from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from difflib import get_close_matches
from pathlib import Path

import duckdb
import yaml

RAIZ = Path(__file__).resolve().parent.parent
SPEC = yaml.safe_load((RAIZ / "semantic" / "metricas.yml").read_text(encoding="utf-8"))
BANCO = Path(os.environ.get("HELPPI_DUCKDB", RAIZ / "helppi.duckdb"))


def hoje() -> date:
    """Data de referência para "semana passada", "mês passado" etc.

    Os dados do case vão até 11/10/2026; por padrão o agente "vive" em
    12/10/2026, para que "semana passada" seja a última semana com dados.
    """
    return date.fromisoformat(os.environ.get("HELPPI_HOJE", "2026-10-12"))


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c)
    ).strip()


def resolver_cliente(nome: str) -> str | None:
    """Traduz "Rede Alfa", "alfa", "C01"... para o código do cliente."""
    alvo = _sem_acento(nome)
    apelidos = {}
    for codigo, nomes in SPEC["clientes"].items():
        apelidos[_sem_acento(codigo)] = codigo
        for n in nomes:
            apelidos[_sem_acento(n)] = codigo
    if alvo in apelidos:
        return apelidos[alvo]
    parecido = get_close_matches(alvo, apelidos, n=1, cutoff=0.75)
    return apelidos[parecido[0]] if parecido else None


@dataclass
class Periodo:
    inicio: date
    fim: date  # inclusivo
    descricao: str


def resolver_periodo(expressao: str) -> Periodo:
    """Traduz expressões de tempo em um intervalo de datas (semanas ISO, seg-dom).

    Aceita: "semana passada", "esta semana", "ultimas N semanas", "mes passado",
    "ultimo mes" (últimos 30 dias), "tudo", uma data ISO (a semana que a contém)
    ou "AAAA-MM-DD..AAAA-MM-DD".
    """
    e = _sem_acento(expressao)
    ref = hoje()
    seg_atual = ref - timedelta(days=ref.weekday())

    if ".." in e:
        a, b = e.split("..")
        return Periodo(date.fromisoformat(a), date.fromisoformat(b), expressao)
    if e in {"semana passada", "ultima semana"}:
        ini = seg_atual - timedelta(days=7)
        return Periodo(ini, ini + timedelta(days=6), f"semana de {ini:%d/%m/%Y}")
    if e in {"esta semana", "semana atual"}:
        return Periodo(seg_atual, seg_atual + timedelta(days=6), f"semana de {seg_atual:%d/%m/%Y}")
    if e.startswith("ultimas") and "semana" in e:
        n = int("".join(ch for ch in e if ch.isdigit()) or 4)
        ini = seg_atual - timedelta(days=7 * n)
        return Periodo(ini, seg_atual - timedelta(days=1), f"últimas {n} semanas")
    if e == "mes passado":
        fim = ref.replace(day=1) - timedelta(days=1)
        return Periodo(fim.replace(day=1), fim, f"{fim:%m/%Y}")
    if e in {"ultimo mes", "ultimos 30 dias"}:
        return Periodo(ref - timedelta(days=30), ref - timedelta(days=1), "últimos 30 dias")
    if e in {"tudo", "todo o periodo", ""}:
        return Periodo(date(2000, 1, 1), date(2100, 1, 1), "todo o período")
    d = date.fromisoformat(e)
    ini = d - timedelta(days=d.weekday())
    return Periodo(ini, ini + timedelta(days=6), f"semana de {ini:%d/%m/%Y}")


def _medida_sql(nome: str) -> str:
    return SPEC["medidas"][nome]["sql"]


def metrica_sql(nome: str) -> str:
    m = SPEC["metricas"][nome]
    if m["tipo"] == "razao":
        return (
            f"({_medida_sql(m['numerador'])})::double"
            f" / nullif({_medida_sql(m['denominador'])}, 0)"
        )
    return _medida_sql(m["medida"])


def consultar(
    metricas: list[str],
    filtros: dict[str, str] | None = None,
    periodo: str = "tudo",
    agrupar_por: list[str] | None = None,
    conexao: duckdb.DuckDBPyConnection | None = None,
) -> dict:
    """Calcula métricas com filtros e agrupamentos declarados na camada semântica."""
    filtros = dict(filtros or {})
    agrupar_por = list(agrupar_por or [])
    for m in metricas:
        if m not in SPEC["metricas"]:
            raise ValueError(f"Métrica desconhecida: {m}. Disponíveis: {list(SPEC['metricas'])}")
    for d in [*filtros, *agrupar_por]:
        if d not in SPEC["dimensoes"]:
            raise ValueError(f"Dimensão desconhecida: {d}. Disponíveis: {list(SPEC['dimensoes'])}")

    if "cliente" in filtros:
        codigo = resolver_cliente(filtros["cliente"])
        if codigo is None:
            raise ValueError(f"Cliente não reconhecido: {filtros['cliente']}")
        filtros["cliente"] = codigo

    p = resolver_periodo(periodo)
    where = ["data_servico between ? and ?"]
    params: list = [p.inicio, p.fim]
    for dim, valor in filtros.items():
        where.append(f"{SPEC['dimensoes'][dim]['sql']} = ?")
        params.append(valor)

    dims_sql = [f"{SPEC['dimensoes'][d]['sql']} as {d}" for d in agrupar_por]
    mets_sql = [f"{metrica_sql(m)} as {m}" for m in metricas]
    sql = (
        f"select {', '.join(dims_sql + mets_sql)}\n"
        f"from {SPEC['modelo_base']} v\n"
        f"left join stg_clientes c using (cliente_id)\n"
        f"where {' and '.join(where)}"
    )
    if agrupar_por:
        ordem = ", ".join(str(i + 1) for i in range(len(agrupar_por)))
        sql += f"\ngroup by {ordem}\norder by {ordem}"

    con = conexao or duckdb.connect(str(BANCO), read_only=True)
    try:
        cur = con.execute(sql, params)
        colunas = [c[0] for c in cur.description]
        linhas = [dict(zip(colunas, row)) for row in cur.fetchall()]
    finally:
        if conexao is None:
            con.close()

    return {
        "periodo": {"inicio": p.inicio.isoformat(), "fim": p.fim.isoformat(), "descricao": p.descricao},
        "filtros": filtros,
        "linhas": [{k: _json(v) for k, v in linha.items()} for linha in linhas],
        "definicoes": {m: SPEC["metricas"][m]["definicao"].strip() for m in metricas},
        "sql": sql,
    }


def _json(v):
    if isinstance(v, date):
        return v.isoformat()
    if v is None or isinstance(v, (int, str, bool)):
        return v
    return round(float(v), 6)
