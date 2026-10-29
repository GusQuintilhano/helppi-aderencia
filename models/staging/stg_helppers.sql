select
    trim(helpper_id)            as helpper_id,
    trim(cidade)                as cidade,
    cast(data_cadastro as date) as data_cadastro
from {{ source('raw', 'helppers') }}
