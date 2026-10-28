-- Una fila por fecha, tomando la descarga más reciente.
WITH expandido AS (
    -- Convierte el arreglo JSON de cada descarga en una fila por día.
    SELECT
        h.descargado_en,
        (e->>'fecha')::date       AS fecha,
        (e->>'promedio')::numeric AS tasa_ves
    FROM {{ source('raw', 'tasa_historico') }} AS h,
         jsonb_array_elements(h.payload) AS e
),
numerado AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY fecha
            ORDER BY descargado_en DESC
        ) AS n
    FROM expandido
)
SELECT fecha, tasa_ves, descargado_en
FROM numerado
WHERE n = 1