-- Entregável: GBV e taxa de aderência por cliente e por semana (semana ISO,
-- segunda a domingo, pela DATA DO SERVIÇO).
with base as (
    select * from {{ ref('fct_vagas') }}
)

select
    b.cliente_id,
    c.cliente_nome,
    b.semana_inicio,

    count(*)                                                       as vagas_abertas,
    count(*) filter (where foi_cancelada_cliente)                  as vagas_canceladas_cliente,
    count(*) filter (where foi_cancelamento_tardio)                as vagas_canceladas_tardias,

    count(*) filter (where conta_como_demanda)                     as vagas_demandadas,
    count(*) filter (where conta_como_demanda and foi_atendida)    as vagas_atendidas,
    round(
        count(*) filter (where conta_como_demanda and foi_atendida)::double
        / nullif(count(*) filter (where conta_como_demanda), 0), 4) as taxa_aderencia,

    -- abertura do que NÃO foi atendido (o "porquê" do número)
    count(*) filter (where conta_como_demanda and desfecho = 'no_show')                   as nao_atendidas_no_show,
    count(*) filter (where conta_como_demanda and desfecho = 'desistencia_sem_reposicao') as nao_atendidas_desistencia,
    count(*) filter (where conta_como_demanda and desfecho = 'sem_alocacao')              as nao_atendidas_sem_alocacao,
    count(*) filter (where conta_como_demanda and desfecho = 'cancelada_cliente')         as nao_atendidas_cancel_tardio,
    count(*) filter (where teve_reposicao)                                                as vagas_com_reposicao,

    -- visão complementar em horas (próxima do faturamento)
    sum(horas_previstas) filter (where conta_como_demanda)        as horas_demandadas,
    sum(horas_realizadas)                                          as horas_realizadas,
    round(sum(horas_realizadas)::double
          / nullif(sum(horas_previstas) filter (where conta_como_demanda), 0), 4) as taxa_aderencia_horas,

    sum(gbv)                                                       as gbv,
    sum(n_realizados_sem_horas)                                    as atendimentos_realizados_sem_horas
from base b
left join {{ ref('stg_clientes') }} c using (cliente_id)
group by all
order by 1, 3
