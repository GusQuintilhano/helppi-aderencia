-- Ponte (waterfall) do número do Dashboard de Operação para o número oficial,
-- aplicando uma correção por vez sobre o total do período.
with a as (
    select
        trim(vaga_id) as vaga_id,
        status as status_cru,
        lower(trim(status)) as status
    from {{ source('raw', 'atendimentos') }}
),
v as (select * from {{ ref('fct_vagas') }}),
passos as (
    select 1 as ordem, '01 Operação (status exato, inclui canceladas)' as passo,
        (select count(distinct vaga_id) from a where status_cru = 'realizado') as num,
        (select count(*) from v) as den
    union all
    select 2, '+ normaliza status (Realizado / espaços)',
        (select count(distinct vaga_id) from a where status = 'realizado'),
        (select count(*) from v)
    union all
    select 3, '+ tira canceladas pelo cliente do denominador = OFICIAL',
        (select count(*) from v where conta_como_demanda and foi_atendida),
        (select count(*) from v where conta_como_demanda)
)
select ordem, passo, num, den, round(100.0 * num / den, 2) as taxa_pct
from passos order by ordem
