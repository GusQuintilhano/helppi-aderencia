-- Consistência entre as duas fontes de cancelamento: vaga cancelada pelo
-- cliente não pode ter atendimento realizado.
select vaga_id from {{ ref('fct_vagas') }}
where foi_cancelada_cliente and foi_atendida
