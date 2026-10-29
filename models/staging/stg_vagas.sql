select
    trim(vaga_id)                                   as vaga_id,
    trim(cliente_id)                                as cliente_id,
    trim(pdv_id)                                    as pdv_id,
    cast(data_servico as date)                      as data_servico,
    lower(trim(tipo_servico))                       as tipo_servico,
    cast(horas_previstas as numeric(5, 2))          as horas_previstas,
    cast(criada_em as timestamp)                    as criada_em,
    cast(nullif(trim(cancelada_cliente_em), '') as timestamp) as cancelada_cliente_em
from {{ source('raw', 'vagas') }}
