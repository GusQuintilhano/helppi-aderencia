-- Preço vigente NA DATA DO SERVIÇO (join por intervalo de vigência).
-- O join sem a vigência (como na query do Financeiro) duplica as vagas
-- de clientes que tiveram reajuste.
select
    v.*,
    p.preco_id,
    p.preco_hora,
    v.horas_realizadas * p.preco_hora as gbv
from {{ ref('int_vagas_desfecho') }} v
left join {{ ref('stg_precos') }} p
       on p.cliente_id   = v.cliente_id
      and p.tipo_servico = v.tipo_servico
      and v.data_servico between p.vigencia_inicio and p.vigencia_fim_efetiva
