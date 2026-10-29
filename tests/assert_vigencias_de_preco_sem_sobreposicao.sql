-- Duas vigências do mesmo cliente+serviço não podem se sobrepor; senão uma
-- vaga casaria com dois preços e o GBV dobraria.
select a.preco_id, b.preco_id as preco_id_conflitante
from {{ ref('stg_precos') }} a
join {{ ref('stg_precos') }} b
  on a.cliente_id = b.cliente_id
 and a.tipo_servico = b.tipo_servico
 and a.preco_id < b.preco_id
 and a.vigencia_inicio <= b.vigencia_fim_efetiva
 and b.vigencia_inicio <= a.vigencia_fim_efetiva
