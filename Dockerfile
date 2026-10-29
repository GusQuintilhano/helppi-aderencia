# Agente MCP em modo HTTP, para clientes remotos (Gemini, claude.ai).
# O dbt roda no build: a imagem já sai com o helppi.duckdb pronto e testado.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PYTHON=/usr/local/bin/python3.12

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv run --no-dev dbt build --profiles-dir . \
    && rm -rf target logs

ENV MCP_TRANSPORT=http PORT=8000 HELPPI_HOJE=2026-10-12
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "python", "-m", "agente.mcp_server"]
