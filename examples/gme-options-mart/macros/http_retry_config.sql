{% macro http_retry_config(timeout_ms=30000, retries=3) %}
    SET http_timeout = {{ timeout_ms }};
    SET http_retries = {{ retries }};
    SET http_retry_wait_ms = 1000;
    SET http_retry_backoff = 2.0;
{% endmacro %}
