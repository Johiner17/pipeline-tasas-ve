import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.types.json import Jsonb

load_dotenv()

# Lista fija de fuentes permitidas. El nombre de la carpeta en data/raw/
# es también el nombre de la tabla en el esquema raw.
FUENTES = ("tasa_oficial", "tasa_historico")


def conectar():
    """Abre una conexión a PostgreSQL con las credenciales del .env."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=5432,
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )


def construir_insert(tabla: str) -> sql.Composed:
    """Arma el INSERT para una tabla del esquema raw.

    Los valores van como %s (se pasan aparte). El nombre de la tabla NO puede
    ir como %s, por eso se inserta con sql.Identifier, que lo escapa bien.
    """
    return sql.SQL(
        "INSERT INTO {tabla} (descargado_en, url_fuente, payload, archivo) "
        "VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (archivo) DO NOTHING"
    ).format(tabla=sql.Identifier("raw", tabla))


def cargar_fuente(conn, fuente: str, base: Path = Path("data/raw")) -> tuple[int, int]:
    """Carga los JSON nuevos de una fuente y devuelve (cargados, omitidos)."""
    # Solo se aceptan fuentes de la lista fija.
    if fuente not in FUENTES:
        raise ValueError(f"Fuente desconocida: {fuente}")

    insert = construir_insert(fuente)
    cargados = omitidos = 0

    for ruta in sorted((base / fuente).glob("*.json")):
        with ruta.open(encoding="utf-8") as archivo:
            sobre = json.load(archivo)

        # Si falta una clave del sobre, el error dice qué archivo la causó.
        try:
            descargado_en = datetime.fromisoformat(sobre["descargado_en"])
            url_fuente = sobre["url_fuente"]
            datos = sobre["datos"]
        except KeyError as error:
            raise ValueError(f"{ruta.name}: falta la clave {error}") from error

        # Jsonb(datos) sirve igual para un diccionario (tasa del día)
        # que para una lista (histórico).
        cursor = conn.execute(
            insert, (descargado_en, url_fuente, Jsonb(datos), ruta.name)
        )

        # rowcount: 1 si insertó, 0 si ON CONFLICT lo omitió.
        if cursor.rowcount == 1:
            cargados += 1
        else:
            omitidos += 1

    return cargados, omitidos


if __name__ == "__main__":
    # Una sola conexión y una sola transacción para todas las fuentes:
    # si una falla, se deshace todo y no queda nada cargado a medias.
    with conectar() as conn:
        for fuente in FUENTES:
            cargados, omitidos = cargar_fuente(conn, fuente)
            print(f"{fuente}: cargados {cargados}, omitidos {omitidos}")