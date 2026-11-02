-- Profiling das tabelas cruas, antes de qualquer modelo.
-- Cada linha é uma checagem; as que acharam problema viraram teste no dbt.
-- Rodar: uv run dbt compile -s profiling e executar target/compiled/.../profiling.sql no DuckDB.
with
v as (select * from {{ source('raw', 'vagas') }}),
a as (select * from {{ source('raw', 'atendimentos') }}),
p as (select * from {{ source('raw', 'precos') }})

select 'atendimento_id duplicado (ids)' as checagem,
    (select count(*) from (select atendimento_id from a group by 1 having count(*) > 1)) as resultado
union all
select 'status fora do padrão lower/trim (linhas)',
    (select count(*) from a where status <> lower(trim(status)))
union all
select 'realizado sem horas_realizadas',
    (select count(*) from a where lower(trim(status)) = 'realizado' and coalesce(trim(horas_realizadas), '') = '')
union all
select 'vagas com desistência + reposição (2 alocações)',
    (select count(*) from (select vaga_id from a group by 1
        having bool_or(lower(trim(status)) = 'desistencia_helpper') and bool_or(lower(trim(status)) = 'realizado')))
union all
select 'clientes com mais de uma vigência de preço',
    (select count(distinct cliente_id) from (select cliente_id, tipo_servico from p group by 1, 2 having count(*) > 1))
union all
select 'canceladas pelo cliente',
    (select count(*) from v where coalesce(cancelada_cliente_em, '') <> '')
union all
select 'canceladas com menos de 12h (até 00h do dia do serviço)',
    (select count(*) from v where coalesce(cancelada_cliente_em, '') <> ''
        and cast(data_servico as timestamp) - cast(cancelada_cliente_em as timestamp) < interval 12 hour)
union all
select 'atendimentos sem vaga correspondente (órfãos)',
    (select count(*) from a left join v using (vaga_id) where v.vaga_id is null)
union all
select 'horas realizadas acima das previstas',
    (select count(*) from a join v using (vaga_id)
        where cast(nullif(trim(a.horas_realizadas), '') as double) > cast(v.horas_previstas as double))
