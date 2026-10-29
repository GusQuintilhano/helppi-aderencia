{% test entre_zero_e_um(model, column_name) %}
select * from {{ model }} where {{ column_name }} < 0 or {{ column_name }} > 1
{% endtest %}

{% test dbt_utils_free_unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
