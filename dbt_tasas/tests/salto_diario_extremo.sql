{{ config(severity='warn') }}

-- Avisa si la tasa cambia más de 20% de un día publicado al siguiente.
-- LAG trae el valor de la fila anterior, ordenada por fecha.
WITH t AS (
    SELECT
        fecha,
        tasa_ves,
        LAG(tasa_ves) OVER (ORDER BY fecha) AS anterior
    FROM {{ ref('stg_tasa_historico') }}
)
SELECT fecha, anterior, tasa_ves
FROM t
WHERE anterior IS NOT NULL
  AND abs(tasa_ves / anterior - 1) > 0.20