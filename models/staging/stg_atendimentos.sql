-- A origem tem linhas duplicadas (mesmo atendimento_id repetido, às vezes com
-- o status em caixa/espaço diferente: 'Realizado', ' realizado '). Normalizamos
-- o status e mantemos uma linha por atendimento_id.
with normalizado as (
    select
        trim(atendimento_id)                          as atendimento_id,
        trim(vaga_id)                                 as vaga_id,
        trim(helpper_id)                              as helpper_id,
        lower(trim(status))                           as status,
        cast(nullif(trim(horas_realizadas), '') as numeric(5, 2)) as horas_realizadas
    from {{ source('raw', 'atendimentos') }}
)

select *
from normalizado
qualify row_number() over (
    partition by atendimento_id
    order by horas_realizadas desc nulls last
) = 1
