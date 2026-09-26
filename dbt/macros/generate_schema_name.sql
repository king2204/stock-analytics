{# Use the custom schema name as-is (staging, marts) instead of dbt's default
   "<target>_<custom>" so the dashboard can query marts.* directly. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name | trim if custom_schema_name else target.schema }}
{%- endmacro %}
