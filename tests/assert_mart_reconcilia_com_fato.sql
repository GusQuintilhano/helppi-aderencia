-- O mart não pode perder nem inventar vaga ou GBV na agregação.
with fato as (
    select count(*) as vagas, coalesce(sum(gbv), 0) as gbv from {{ ref('fct_vagas') }}
),
mart as (
    select sum(vagas_abertas) as vagas, coalesce(sum(gbv), 0) as gbv
    from {{ ref('mart_aderencia_gbv_cliente_semana') }}
)
select * from fato, mart
where fato.vagas <> mart.vagas or abs(fato.gbv - mart.gbv) > 0.01
