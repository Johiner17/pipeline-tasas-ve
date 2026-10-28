-- Capa staging: datos limpios, tipados y sin duplicados.
CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE VIEW staging.stg_tasa_historico AS
WITH expandido AS (
    -- jsonb_array_elements convierte el arreglo de cada descarga
    -- en una fila por día. "e" es cada elemento del arreglo.
    SELECT
        h.descargado_en,
        (e->>'fecha')::date       AS fecha,      -- texto -> fecha
        (e->>'promedio')::numeric AS tasa_ves    -- texto -> número
    FROM raw.tasa_historico AS h,
         jsonb_array_elements(h.payload) AS e
),
numerado AS (
    -- Numera las filas de cada fecha: la descarga más reciente es la 1.
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY fecha
            ORDER BY descargado_en DESC
        ) AS n
    FROM expandido
)
-- Nos quedamos con una sola fila por fecha: la más reciente.
SELECT fecha, tasa_ves, descargado_en
FROM numerado
WHERE n = 1;