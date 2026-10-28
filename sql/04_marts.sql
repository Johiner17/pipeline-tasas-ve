-- Capa marts: tabla lista para que la usen los analistas.
CREATE SCHEMA IF NOT EXISTS marts;

CREATE OR REPLACE VIEW marts.fct_tasa_diaria AS
WITH calendario AS (
    -- Una fila por cada día, del primero al último dato disponible.
    SELECT d::date AS fecha
    FROM generate_series(
        (SELECT min(fecha) FROM staging.stg_tasa_historico),
        (SELECT max(fecha) FROM staging.stg_tasa_historico),
        interval '1 day'
    ) AS d
)
SELECT
    c.fecha,
    u.tasa_ves,
    -- Fecha de la tasa que realmente se está usando ese día.
    u.fecha AS fecha_tasa,
    -- TRUE si el BCV publicó tasa ese día; FALSE si la rellenamos.
    (s.fecha IS NOT NULL) AS es_dia_publicado
FROM calendario AS c
LEFT JOIN staging.stg_tasa_historico AS s
    ON s.fecha = c.fecha
-- LATERAL busca, para cada día, la última tasa publicada hasta esa fecha.
-- Es el "forward fill": sábado y domingo toman la del viernes.
LEFT JOIN LATERAL (
    SELECT fecha, tasa_ves
    FROM staging.stg_tasa_historico
    WHERE fecha <= c.fecha
    ORDER BY fecha DESC
    LIMIT 1
) AS u ON TRUE;