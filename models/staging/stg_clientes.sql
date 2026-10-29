select
    trim(cliente_id) as cliente_id,
    trim(nome)       as cliente_nome,
    trim(segmento)   as segmento
from {{ source('raw', 'clientes') }}
