select
    cast(preco_id as integer)                        as preco_id,
    trim(cliente_id)                                 as cliente_id,
    lower(trim(tipo_servico))                        as tipo_servico,
    cast(preco_hora as numeric(10, 2))               as preco_hora,
    cast(vigencia_inicio as date)                    as vigencia_inicio,
    cast(nullif(trim(vigencia_fim), '') as date)     as vigencia_fim,
    -- fim aberto vira data-sentinela para facilitar o join por intervalo
    coalesce(cast(nullif(trim(vigencia_fim), '') as date), date '9999-12-31') as vigencia_fim_efetiva
from {{ source('raw', 'precos') }}
