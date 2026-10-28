-- Falla si el dato más reciente tiene más de 4 días de atraso.
-- Detecta un pipeline detenido o una fuente caída.
SELECT max(fecha) AS ultima_fecha
FROM {{ ref('stg_tasa_historico') }}
HAVING max(fecha) < current_date - 4