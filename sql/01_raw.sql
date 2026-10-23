CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.tasa_oficial (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    descargado_en TIMESTAMPTZ NOT NULL,
    url_fuente    TEXT        NOT NULL,
    payload       JSONB       NOT NULL,
    archivo       TEXT        NOT NULL UNIQUE
);