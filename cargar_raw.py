import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

# Lee el archivo .env y deja sus variables disponibles en os.getenv(...)
load_dotenv()

# %s son "huecos" que se llenan aparte con valores (consulta parametrizada).
# Nunca se pegan los valores dentro del texto SQL: así la base los trata como
# datos y no como código (defensa contra inyección SQL).
# ON CONFLICT (archivo) DO NOTHING: si ese archivo ya está cargado, no falla
# ni lo duplica, simplemente no inserta nada. Eso es la idempotencia.
SQL_INSERT = """
INSERT INTO raw.tasa_oficial (descargado_en, url_fuente, payload, archivo)
VALUES (%s, %s, %s, %s)
ON CONFLICT (archivo) DO NOTHING
"""


def conectar():
    """Abre una conexión a PostgreSQL con las credenciales del .env."""
    return psycopg.connect(
        host="localhost",
        port=5432,
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )


def cargar_archivos(carpeta: Path = Path("data/raw")) -> tuple[int, int]:
    """Carga los JSON nuevos y devuelve (cargados, omitidos)."""
    cargados = omitidos = 0

    # "with" abre la conexión y la cierra sola al terminar el bloque.
    # Si todo salió bien, confirma los cambios (commit); si hubo un error,
    # los deshace (rollback). Así no quedan cargas a medias.
    with conectar() as conn:
        # glob("*.json") lista los archivos .json de la carpeta.
        # sorted() los ordena por nombre, que como lleva la fecha, es
        # también orden cronológico.
        for ruta in sorted(carpeta.glob("*.json")):

            # 1. Leer el JSON del archivo y convertirlo en diccionario.
            with ruta.open(encoding="utf-8") as archivo:
                sobre = json.load(archivo)

            # 2. Insertar. Cada valor va en el mismo orden que los %s de arriba.
            #    - descargado_en: texto ISO -> datetime, para que sea una fecha real
            #    - url_fuente: de dónde vino el dato
            #    - Jsonb(...): le dice a psycopg que esto va a una columna JSONB
            #    - ruta.name: solo el nombre del archivo; es la clave UNIQUE
            cursor = conn.execute(
                SQL_INSERT,
                (
                    datetime.fromisoformat(sobre["descargado_en"]),
                    sobre["url_fuente"],
                    Jsonb(sobre["datos"]),
                    ruta.name,
                ),
            )

            # 3. rowcount = filas afectadas por el INSERT.
            #    1 -> se insertó (archivo nuevo)
            #    0 -> ON CONFLICT lo omitió (ya estaba cargado)
            if cursor.rowcount == 1:
                cargados += 1
            else:
                omitidos += 1

    return cargados, omitidos


# Solo corre si ejecutas este archivo directamente (python cargar_raw.py).
# Si otro archivo lo importa, no se ejecuta nada. Igual que en ingesta.py.
if __name__ == "__main__":
    cargados, omitidos = cargar_archivos()
    print(f"cargados: {cargados}, omitidos: {omitidos}")