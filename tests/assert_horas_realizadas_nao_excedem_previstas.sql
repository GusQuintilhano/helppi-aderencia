{{ config(severity = 'warn') }}
select vaga_id, horas_previstas, horas_realizadas
from {{ ref('fct_vagas') }}
where horas_realizadas > horas_previstas
