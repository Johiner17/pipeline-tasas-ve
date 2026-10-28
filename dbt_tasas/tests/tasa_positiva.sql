-- Falla si hay alguna tasa cero o negativa.
SELECT fecha, tasa_ves
FROM {{ ref('stg_tasa_historico') }}
WHERE tasa_ves <= 0