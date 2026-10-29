-- Atendimento 'realizado' sem horas_realizadas deixa de ser faturado.
-- WARN (não bloqueia o pipeline), mas precisa virar ação na operação.
{{ config(severity = 'warn') }}
select atendimento_id, vaga_id
from {{ ref('stg_atendimentos') }}
where status = 'realizado' and horas_realizadas is null
