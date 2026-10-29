"""Servidor MCP de métricas da Helppi.

O agente de IA não escreve SQL: ele chama estas ferramentas, que só calculam
métricas declaradas em semantic/metricas.yml. Assim a resposta do agente é,
por construção, o mesmo número do mart que alimenta o dashboard.

Rodar:  uv run python -m agente.mcp_server   (stdio; ver .mcp.json)
Remoto: MCP_TRANSPORT=http MCP_TOKEN=... uv run python -m agente.mcp_server
        (streamable HTTP em /mcp/<token>; ver Dockerfile)
"""

from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from semantic import engine

servidor = MCPServer(
    name="helppi-metricas",
    instructions=(
        "Métricas oficiais da Helppi (taxa de aderência, GBV). Sempre: "
        "1) resolva o cliente com resolver_cliente; 2) passe expressões de tempo "
        "('semana passada', 'mes passado') direto em `periodo`; 3) responda com o "
        "número, o período exato e a definição usada. Para 'o que puxou para baixo', "
        "use explicar_aderencia. Nunca estime um número que a ferramenta não retornou."
    ),
)


@servidor.tool()
def listar_metricas() -> dict:
    """Lista as métricas oficiais, suas definições e as dimensões disponíveis."""
    return {
        "metricas": {
            nome: {"rotulo": m["rotulo"], "definicao": m["definicao"].strip(), "dono": m["dono"]}
            for nome, m in engine.SPEC["metricas"].items()
        },
        "dimensoes": {nome: d["descricao"] for nome, d in engine.SPEC["dimensoes"].items()},
        "data_referencia_hoje": engine.hoje().isoformat(),
    }


@servidor.tool()
def resolver_cliente(nome: str) -> dict:
    """Traduz o nome de um cliente ("Rede Alfa", "farmácias gama") para o código (C01...)."""
    codigo = engine.resolver_cliente(nome)
    if codigo is None:
        return {"encontrado": False, "clientes": engine.SPEC["clientes"]}
    return {"encontrado": True, "cliente": codigo, "nome": engine.SPEC["clientes"][codigo][0]}


@servidor.tool()
def consultar_metrica(
    metricas: list[str],
    periodo: str = "tudo",
    cliente: str | None = None,
    cidade: str | None = None,
    agrupar_por: list[str] | None = None,
) -> dict:
    """Calcula métricas oficiais.

    metricas: ex. ["taxa_aderencia", "gbv"].
    periodo: "semana passada", "mes passado", "ultimas 4 semanas", "tudo",
             uma data ISO (semana que a contém) ou "2026-09-01..2026-09-30".
    cliente: nome ou código; cidade: nome da cidade.
    agrupar_por: dimensões, ex. ["semana"], ["cidade"], ["desfecho"].
    """
    filtros = {k: v for k, v in {"cliente": cliente, "cidade": cidade}.items() if v}
    resultado = engine.consultar(metricas, filtros, periodo, agrupar_por)
    resultado.pop("sql")
    return resultado


@servidor.tool()
def explicar_aderencia(cliente: str | None = None, periodo: str = "ultimo mes") -> dict:
    """Explica o que puxou a aderência para baixo: motivos, PDVs e dias da semana piores."""
    filtros = {"cliente": cliente} if cliente else {}
    geral = engine.consultar(
        ["taxa_aderencia", "vagas_demandadas", "vagas_atendidas", "gbv", "gbv_nao_capturado"],
        filtros, periodo,
    )
    motivos = engine.consultar(["vagas_demandadas", "gbv_nao_capturado"], filtros, periodo, ["desfecho"])
    pdvs = engine.consultar(["taxa_aderencia", "vagas_demandadas"], filtros, periodo, ["pdv", "cidade"])
    dias = engine.consultar(["taxa_aderencia", "vagas_demandadas"], filtros, periodo, ["dia_semana"])
    semanas = engine.consultar(["taxa_aderencia", "gbv"], filtros, periodo, ["semana"])

    nao_atendidas = [
        linha for linha in motivos["linhas"]
        if linha["desfecho"] not in ("atendida", "cancelada_cliente")
    ]
    return {
        "periodo": geral["periodo"],
        "filtros": geral["filtros"],
        "resumo": geral["linhas"][0],
        "nao_atendidas_por_motivo": sorted(nao_atendidas, key=lambda l: -l["vagas_demandadas"]),
        "piores_pdvs": sorted(pdvs["linhas"], key=lambda l: l["taxa_aderencia"] or 0)[:3],
        "por_dia_da_semana": sorted(dias["linhas"], key=lambda l: l["taxa_aderencia"] or 0),
        "por_semana": semanas["linhas"],
        "definicao": geral["definicoes"]["taxa_aderencia"],
    }


def servir_http() -> None:
    """Expõe o servidor por HTTP para clientes remotos (Gemini, claude.ai).

    O token entra no caminho da URL porque nem todo cliente remoto deixa
    configurar um cabeçalho de autenticação.
    """
    token = os.environ.get("MCP_TOKEN")
    if not token:
        raise SystemExit("MCP_TOKEN é obrigatório no modo http")
    servidor.run(
        "streamable-http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        streamable_http_path=f"/mcp/{token}",
        stateless_http=True,
        # Atrás do proxy reverso o Host é o domínio público; o token protege a rota.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "http":
        servir_http()
    else:
        servidor.run()
