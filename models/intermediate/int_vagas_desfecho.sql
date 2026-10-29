-- Uma linha por vaga, com o desfecho consolidado de todas as alocações.
-- Uma vaga pode ter várias alocações (ex.: desistência seguida de reposição);
-- a vaga conta como atendida se QUALQUER alocação foi realizada.
with alocacoes as (
    select
        vaga_id,
        count(*)                                                        as n_alocacoes,
        count(*) filter (where status = 'realizado')                    as n_realizados,
        count(*) filter (where status = 'no_show')                      as n_no_show,
        count(*) filter (where status = 'desistencia_helpper')          as n_desistencias,
        count(*) filter (where status = 'realizado' and horas_realizadas is null) as n_realizados_sem_horas,
        sum(horas_realizadas) filter (where status = 'realizado')       as horas_realizadas
    from {{ ref('stg_atendimentos') }}
    group by 1
),

vagas as (
    select
        v.*,
        p.cidade,
        v.cancelada_cliente_em is not null as foi_cancelada_cliente,
        date_diff('hour', v.cancelada_cliente_em, cast(v.data_servico as timestamp)) as horas_antecedencia_cancelamento
    from {{ ref('stg_vagas') }} v
    left join {{ ref('stg_pdvs') }} p using (pdv_id)
)

select
    v.vaga_id,
    v.cliente_id,
    v.pdv_id,
    v.cidade,
    v.data_servico,
    cast(date_trunc('week', v.data_servico) as date)           as semana_inicio,
    v.tipo_servico,
    v.horas_previstas,
    v.criada_em,
    v.cancelada_cliente_em,
    v.foi_cancelada_cliente,
    v.horas_antecedencia_cancelamento,
    coalesce(v.foi_cancelada_cliente
             and v.horas_antecedencia_cancelamento < {{ var('cancelamento_tardio_horas') }}, false)
                                                               as foi_cancelamento_tardio,
    coalesce(a.n_alocacoes, 0)                                 as n_alocacoes,
    coalesce(a.n_realizados, 0) > 0                            as foi_atendida,
    coalesce(a.n_desistencias, 0) > 0 and coalesce(a.n_realizados, 0) > 0 as teve_reposicao,
    coalesce(a.n_realizados_sem_horas, 0)                      as n_realizados_sem_horas,
    coalesce(a.horas_realizadas, 0)                            as horas_realizadas,
    case
        when v.foi_cancelada_cliente           then 'cancelada_cliente'
        when coalesce(a.n_realizados, 0) > 0   then 'atendida'
        when coalesce(a.n_no_show, 0) > 0      then 'no_show'
        when coalesce(a.n_desistencias, 0) > 0 then 'desistencia_sem_reposicao'
        else 'sem_alocacao'
    end                                                        as desfecho
from vagas v
left join alocacoes a using (vaga_id)
