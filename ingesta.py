import json
from datetime import datetime
from pathlib import Path

import requests

URL = "https://ve.dolarapi.com/v1/dolares/oficial"


def obtener_tasa_oficial() -> dict:
    """Llama a la API y devuelve la respuesta como diccionario."""
    # 1. haz el GET a URL con timeout=10
    respuesta = requests.get(URL, timeout=10)
    # 2. verifica que no haya error HTTP
    respuesta.raise_for_status()
    # 3. devuelve el JSON como diccionario
    return respuesta.json()


def guardar_crudo(datos: dict) -> Path:
    """Guarda los datos originales de la tasa y devuelve la ruta creada."""
    carpeta = Path("data/raw")
    carpeta.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now().astimezone()

    nombre_archivo = f"tasa_oficial_{ahora.strftime('%Y%m%dT%H%M%S')}.json"
    ruta = carpeta / nombre_archivo
    contenido = {
        "descargado_en": ahora.isoformat(),
        "url_fuente": URL,
        "datos": datos,
    }
    with ruta.open("w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)

    return ruta


if __name__ == "__main__":
    datos = obtener_tasa_oficial()
    guardar_crudo(datos)
    print(datos)
    # 4. imprime solo el campo "promedio" y el campo "fechaActualizacion"
    print(datos["promedio"])
    print(datos["fechaActualizacion"])