-- Fato no grão de VAGA: a base única de onde sai todo número de aderência e GBV.
-- Dashboard, report comercial, fechamento e agente de IA devem ler daqui
-- (ou do mart agregado), nunca das tabelas cruas.
select
    vaga_id,
    cliente_id,
    pdv_id,
    cidade,
    data_servico,
    semana_inicio,
    tipo_servico,
    horas_previstas,
    criada_em,
    cancelada_cliente_em,
    foi_cancelada_cliente,
    foi_cancelamento_tardio,
    horas_antecedencia_cancelamento,
    n_alocacoes,
    teve_reposicao,
    desfecho,

    -- Definição oficial da taxa de aderência (ver README):
    -- denominador = vagas demandadas; numerador = vagas demandadas e atendidas.
    case
        when not foi_cancelada_cliente then true
        when foi_cancelamento_tardio and {{ var('cancelamento_tardio_conta_como_demanda') }} then true
        else false
    end                                              as conta_como_demanda,
    foi_atendida,

    horas_realizadas,
    n_realizados_sem_horas,
    preco_id,
    preco_hora,
    gbv
from {{ ref('int_vagas_precificadas') }}
