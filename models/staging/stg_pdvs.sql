select
    trim(pdv_id)     as pdv_id,
    trim(cliente_id) as cliente_id,
    trim(cidade)     as cidade
from {{ source('raw', 'pdvs') }}
