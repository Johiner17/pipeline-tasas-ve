CREATE TABLE IF NOT EXISTS raw.tasa_historico (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    descargado_en TIMESTAMPTZ NOT NULL,
    url_fuente    TEXT        NOT NULL,
    payload       JSONB       NOT NULL,
    archivo       TEXT        NOT NULL UNIQUE
);