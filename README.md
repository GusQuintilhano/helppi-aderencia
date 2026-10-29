# Helppi — Taxa de aderência e GBV (case Analytics Engineer)

Um número só de **taxa de aderência** e **GBV** por cliente e semana, modelado em dbt + DuckDB a partir dos CSVs do case.

**Resultado do período (31/08 a 11/10/2026):** aderência **85,0%** (1.326 de 1.560 vagas demandadas) · GBV **R$ 244.105**.
As três queries legadas davam 77,1% (Operação), 85,4% (Comercial) e 71,3% em horas com GBV de R$ 308.082 (Financeiro).

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run dbt build --profiles-dir .
```

`dbt build` cria os modelos em `helppi.duckdb` e roda os 47 testes (44 PASS, 3 WARN; os WARN são problemas de qualidade da origem, vistos na seção 1).
O entregável é a tabela `mart_aderencia_gbv_cliente_semana`.

```bash
uv run dbt show --profiles-dir . -s mart_aderencia_gbv_cliente_semana --limit 30
uv run dbt compile --profiles-dir . -s ponte_legado_para_oficial   # ponte do número legado para o oficial
```

## 1. Diagnóstico: por que as três queries não batem

### Problemas nos dados (afetam as três)

| Problema | Tamanho | Efeito |
|---|---|---|
| `atendimento_id` duplicado | 6 ids (12 linhas) | Conta e soma duas vezes |
| Status fora do padrão (`Realizado`, `' realizado '`) | 28 linhas | `status = 'realizado'` não encontra essas linhas |
| `realizado` sem `horas_realizadas` | 4 atendimentos (~R$ 838) | Somem do GBV, ou seja, horas que não são faturadas |
| Vaga com mais de uma alocação (desistência seguida de reposição) | 52 vagas | Join vaga→atendimento multiplica linhas |
| Preço com duas vigências (C02 e C04, reajuste em 21/09) | 2 clientes | Join sem vigência multiplica linhas |

### Query por query

**01 Operação: 77,1%**
- Compara o status com `= 'realizado'` exato, sem `lower/trim`, e perde 27 vagas atendidas.
- Mantém as 125 vagas canceladas pelo cliente no denominador, o que pune a Helppi por uma decisão do cliente.
- `vagas_abertas` usa `COUNT(*)` depois do join, então dá 1.743 e não 1.685. A taxa usa `COUNT(DISTINCT)`, por isso a coluna exibida não bate com a própria taxa.

**02 Comercial: 85,4% (é o relatório enviado ao cliente)**
- Agrupa a semana por **`criada_em`** em vez de `data_servico`. O número da semana vira "vagas abertas naquela semana", gera 8 semanas, inclusive 17/08 e 24/08 (antes do período), e deixa a última semana quase vazia.
- O numerador é `COUNT(atendimento_id)` e não vagas: duplicatas entram duas vezes (1.332 contra 1.326 vagas reais). Isso também permite passar de 100%.
- Exclui as canceladas pelo cliente, que é a escolha certa.

**03 Financeiro: 71,3% em horas, GBV R$ 308.082 (+26%)**
- Junta com `precos` **sem filtrar a vigência**. Toda vaga da C02 e da C04 casa com dois preços e é contada duas vezes: horas, horas previstas e GBV dobram nesses clientes. Só isso responde por R$ 62,8 mil a mais.
- Soma `horas_previstas` depois do join com atendimentos, então vagas com reposição entram duas vezes no denominador.
- As duplicatas de atendimento somam mais R$ 1,1 mil.
- Mantém as canceladas no denominador.
- Mede outra coisa (horas, não vagas): uma vaga de 8h feita em 6h conta 75%.

**Ponte do total (`analyses/ponte_legado_para_oficial.sql`):**

| Passo | Atendidas | Base | Taxa |
|---|---|---|---|
| Query 01 da Operação | 1.299 | 1.685 | 77,1% |
| + normalizar o status | 1.326 | 1.685 | 78,7% |
| + tirar do denominador as canceladas pelo cliente = **oficial** | 1.326 | 1.560 | **85,0%** |

## 2. Definição da taxa de aderência

> **Taxa de aderência** = vagas demandadas que foram atendidas ÷ vagas demandadas

| Item | Definição |
|---|---|
| **Grão** | Vaga (uma unidade de demanda do cliente). O fato `fct_vagas` tem uma linha por vaga. |
| **Denominador: vaga demandada** | Vaga aberta pelo cliente e **não cancelada pelo cliente** |
| **Numerador: vaga atendida** | Vaga demandada com **pelo menos um** atendimento `realizado` (status normalizado, sem duplicatas). Uma reposição depois de desistência conta como atendida. |
| **Exclusões** | Vagas canceladas pelo cliente (`cancelada_cliente_em` preenchido) |
| **Tempo** | Semana ISO (segunda a domingo) da **data do serviço**, quando a demanda acontece. Premissa: timestamps em horário de São Paulo. |
| **Não atendidas, abertas por motivo** | `no_show`, `desistencia_sem_reposicao`, `sem_alocacao` (o campo `desfecho`) |
| **Métrica complementar** | Aderência em horas = horas realizadas ÷ horas previstas das vagas demandadas (81,2%) |
| **GBV** | Σ horas realizadas × preço/hora **vigente na data do serviço** (cliente + tipo de serviço), na semana da data do serviço |

### O que foi decisão técnica (tomei e documentei)

- Remover duplicatas de `atendimento_id` e normalizar o status no staging.
- Grão de vaga, consolidando as várias alocações num único desfecho.
- Join de preço pela vigência, protegido por teste contra sobreposição de vigências.
- Semana pela data do serviço, para que aderência e GBV fiquem no mesmo eixo de tempo.
- Atendimento `realizado` sem horas: **conta como atendido** na aderência, **não entra no GBV** (sem imputar valor) e sai num teste WARN e na coluna `atendimentos_realizados_sem_horas`.

### O que eu levaria para o negócio decidir

1. **Cancelamento tardio.** 66 das 125 canceladas foram canceladas com menos de 12h de antecedência. Se cancelamento tardio contar como demanda não atendida, a taxa cai para **81,6%**. O dbt já tem a chave: `cancelamento_tardio_conta_como_demanda` e `cancelamento_tardio_horas`. Isso também afeta a cobrança de taxa de cancelamento.
2. **Métrica principal em vagas ou em horas?** Recomendo vagas como KPI (responde "atendemos a demanda?") e horas como métrica secundária, ligada ao faturamento. Uma vaga parcial (6h de 8h) é "atendida"?
3. **Qual corte de semana o cliente enxerga.** O relatório comercial hoje usa a data de criação. Trocar muda o número que o cliente já recebe e precisa ser comunicado.
4. **Atendimento realizado sem horas:** faturar pelas horas previstas ou cobrar a correção na origem?

## 3. Modelagem

```
sources (CSV cru, tudo como texto)
└── staging      stg_vagas, stg_atendimentos (normalização + dedup), stg_precos, stg_clientes, stg_pdvs, stg_helppers
    └── intermediate  int_vagas_desfecho (1 linha/vaga, desfecho consolidado)
                      int_vagas_precificadas (preço vigente + GBV)
        └── marts     fct_vagas (grão vaga, base semântica)
                      mart_aderencia_gbv_cliente_semana (entregável)
```

**Testes (47):** unique/not_null/relationships/accepted_values em todas as chaves; vigências de preço sem sobreposição; toda vaga com preço; vaga cancelada não pode ter atendimento realizado; o mart bate com o fato em vagas e GBV; taxas entre 0 e 1; unicidade de cliente×semana. **WARN** na origem (duplicatas, status sujo, realizado sem horas): não param o pipeline, mas ficam visíveis.

## 4. Entregável

`mart_aderencia_gbv_cliente_semana`: cliente × semana com vagas abertas, canceladas, canceladas tardias, demandadas e atendidas, `taxa_aderencia`, a abertura das não atendidas (no-show, desistência, sem alocação), vagas com reposição, horas, `taxa_aderencia_horas`, `gbv` e atendimentos sem horas.

| Cliente | Aderência | Aderência em horas | GBV |
|---|---|---|---|
| C01 Rede Alfa | 88,4% | 84,9% | R$ 59.848 |
| C02 Atacado Beta | 76,2% | 72,2% | R$ 30.325 |
| C03 Farmácias Gama | 89,6% | 85,5% | R$ 63.602 |
| C04 Casa Delta | 79,6% | 76,5% | R$ 32.022 |
| C05 Mercado Épsilon | 85,4% | 81,6% | R$ 58.308 |
| **Total** | **85,0%** | **81,2%** | **R$ 244.105** |

O que mais puxa a aderência para baixo: **vaga sem alocação** (103 vagas, 44% das não atendidas), seguida de no-show (85) e desistência sem reposição (46). **Domingo** fica em 74,6% e os outros dias entre 82% e 89%. Osasco é a cidade mais baixa (80,5%).

## 5. Bônus: agente de IA com o mesmo número do dashboard

**Princípio: a definição mora em um lugar só, e dashboard e IA leem desse lugar. A IA nunca escreve SQL sobre tabela crua.**

1. **Transformação:** dbt (Core) sobre Postgres. A réplica é só leitura, então os modelos vão para um banco/schema `analytics` separado (Postgres pequeno ou um warehouse) e a réplica fica como fonte. Orquestração diária ou horária, com os testes como portão: se um teste quebra, o número não é publicado.
2. **Definição do KPI:** no repositório dbt. `fct_vagas` + YAML com a métrica declarada (dbt Semantic Layer/MetricFlow: medidas `vagas_demandadas` e `vagas_atendidas`, métrica de razão `taxa_aderencia`, dimensões cliente/cidade/PDV/tempo). Tem dono, passa por PR e fica versionada. Mudar a definição é um PR revisado, nunca uma edição solta no Grafana.
3. **Grafana:** lê só os marts e as métricas, nunca a réplica crua.
4. **Agente:** acessa por um servidor **MCP** de métricas, com ferramentas como `consultar_metrica(metrica, filtros, periodo)` e `listar_metricas()`, apoiado na mesma camada semântica (o dbt tem servidor MCP próprio). O LLM só resolve a intenção: "cliente X" vira `C01` por um glossário de entidades, "semana passada" vira a semana ISO anterior no fuso de SP. Quem calcula é a camada semântica. A resposta vem com o número, a definição usada e o período, e o agente pode abrir o motivo usando o `desfecho`.
5. **Garantia de que é o mesmo número:** um conjunto de perguntas de referência roda no CI e compara a resposta do agente com o valor do mart/dashboard. Divergência quebra o build. Permissão por cliente (RLS) vale igual para dashboard, agente e portal.

### Implementado neste repositório

O bônus não ficou só no papel. Esta é uma versão mínima e funcional da arquitetura acima:

| Peça | Arquivo | O que faz |
|---|---|---|
| Camada semântica | `semantic/metricas.yml` | Medidas, métricas (com dono e definição), dimensões e glossário de clientes, tudo declarado uma vez |
| Motor | `semantic/engine.py` | Monta o SQL sobre `fct_vagas` a partir do YAML. Resolve "Rede Alfa" para `C01` e "semana passada" para a semana ISO anterior |
| Servidor MCP | `agente/mcp_server.py` | Expõe `listar_metricas`, `resolver_cliente`, `consultar_metrica` e `explicar_aderencia` para qualquer cliente MCP |
| Paridade | `pytests/test_paridade.py` | Compara as 30 células cliente×semana com o mart e roda 4 perguntas de referência. Se as duas definições divergirem, o teste quebra |

```bash
uv run pytest                                   # paridade agente × mart
uv run python -m semantic.consulta taxa_aderencia gbv --cliente "Rede Alfa" --periodo "semana passada"
claude                                          # no diretório do repo: o .mcp.json registra o servidor helppi-metricas
```

**Remoto (Gemini, claude.ai):** com `MCP_TRANSPORT=http` o mesmo servidor fala streamable HTTP em `/mcp/<MCP_TOKEN>`. O `Dockerfile` roda o `dbt build` no build da imagem, então o container já sobe com o banco pronto e testado. Publicado atrás de HTTPS, a URL é cadastrada como app personalizado no Gemini, como `httpUrl` no Gemini CLI ou como conector no claude.ai: o mesmo número em qualquer modelo.

Premissa da demo: o agente considera que hoje é 12/10/2026 (`HELPPI_HOJE`), o dia seguinte ao fim dos dados, então "semana passada" é a semana de 05/10.

**GBV não capturado:** a camada semântica tem uma métrica nova, `gbv_nao_capturado` (horas previstas × preço vigente das vagas demandadas não atendidas). No período ela soma **R$ 45,3 mil**, 19% do GBV realizado. Por motivo: sem alocação R$ 20,2 mil, no-show R$ 16,1 mil, desistência sem reposição R$ 9,1 mil. Nesta base, 1 ponto de aderência vale cerca de R$ 500 por semana. Também testei se C02 e C04 pioraram depois do reajuste de 21/09: não pioraram (+3,8 e +3,3 pp, com amostra pequena).

## 6. Bônus 2: seis situações, seis entregas

| Situação | Entrega | Por quê |
|---|---|---|
| Gerente de operações abre toda manhã a aderência de ontem por cidade e cliente | **Dashboard** (Grafana, D-1 atualizado antes das 7h) + resumo no Slack | Rotina fixa, mesmas cortes todo dia, consulta rápida |
| Diretor comercial entra em reunião em 10 min e quer saber o último mês do cliente e o que puxou para baixo | **Agente de IA** | Pergunta pontual, urgente, em linguagem natural, que precisa de abertura (desfecho, PDV, dia da semana) |
| Pricing quer saber se o aumento de repasse no domingo melhorou a aderência | **Análise ad hoc** | Pergunta causal e única: diferença-em-diferenças domingo vs. outros dias, antes e depois, controlando demanda e oferta de Helppers. Hoje domingo é o pior dia (74,6%) |
| Operação precisa saber com antecedência quando um PDV corre risco de não preencher as vagas de amanhã | **Alerta** | Precisa ser proativo e acionável: em T-18h, vagas de amanhã sem alocação acima do esperado pela curva histórica de preenchimento → Slack/WhatsApp para o responsável |
| Board recebe todo mês GBV, aderência e margem | **Relatório** mensal fechado | Números congelados (snapshot), comparáveis mês a mês, com comentário. Margem exige dados de repasse/custo que não estão no case |
| Varejista cliente quer acompanhar a aderência das próprias lojas | **Dashboard externo/embutido** (portal do cliente) com RLS por cliente | Autosserviço, substitui o relatório enviado por e-mail. Mesma definição que a Helppi usa internamente |

**O que têm em comum por baixo:** a mesma base governada (`fct_vagas` + definição da métrica + testes). As seis entregas mudam só a **interface** (puxar ou empurrar, humano ou agente), a **latência** (tempo real, D-1, mensal) e o **controle de acesso**. Se a métrica estiver certa num lugar só, qualquer uma delas é barata de construir. Se não estiver, cada uma vira mais uma "query que não bate".

## Premissas e o que eu faria com mais tempo

**Premissas:** timestamps em horário de São Paulo; semana ISO começando na segunda; cancelamento tardio = menos de 12h antes do início do dia do serviço (não há horário de início do turno); a cidade do PDV é a cidade da vaga.

**Com mais tempo:**
- Migrar `semantic/metricas.yml` para o dbt Semantic Layer (MetricFlow) e gerar o mart a partir dele.
- Snapshot (SCD2) de vagas e atendimentos para auditar mudanças de status.
- Freshness nas sources.
- Testes unitários do dbt para os casos de borda (reposição, cancelamento tardio).
- Modelo de risco de preenchimento para o alerta.
- CI com `dbt build` em cada PR.
