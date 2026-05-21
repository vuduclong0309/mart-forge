{% macro http_read_json(url, max_object_size=10485760) %}
    read_json_auto('{{ url }}', maximum_object_size={{ max_object_size }})
{% endmacro %}
