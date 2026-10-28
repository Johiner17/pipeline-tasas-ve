-- Calendario completo: fines de semana y feriados toman la última tasa publicada.
WITH calendario AS (
    SELECT d::date AS fecha
    FROM generate_series(
        (SELECT min(fecha) FROM {{ ref('stg_tasa_historico') }}),
        (SELECT max(fecha) FROM {{ ref('stg_tasa_historico') }}),
        interval '1 day'
    ) AS d
)
SELECT
    c.fecha,
    u.tasa_ves,
    u.fecha AS fecha_tasa,
    (s.fecha IS NOT NULL) AS es_dia_publicado
FROM calendario AS c
LEFT JOIN {{ ref('stg_tasa_historico') }} AS s
    ON s.fecha = c.fecha
LEFT JOIN LATERAL (
    SELECT fecha, tasa_ves
    FROM {{ ref('stg_tasa_historico') }}
    WHERE fecha <= c.fecha
    ORDER BY fecha DESC
    LIMIT 1
) AS u ON TRUE