"""Dashboard de la tasa oficial USD/VES.

Lee marts.fct_tasa_diaria (PostgreSQL) y muestra la serie diaria, marcando
los días en que la tasa fue rellenada (el BCV no publicó ese día).
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import psycopg
import streamlit as st

st.set_page_config(page_title="Tasa USD/VES", layout="wide")

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def conectar():
    """Abre una conexión con las credenciales que llegan por variables de entorno."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=5432,
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )


# cache_data guarda el resultado 10 minutos para no consultar la base en cada clic.
@st.cache_data(ttl=600)
def cargar_datos() -> pd.DataFrame:
    consulta = """
        SELECT fecha, tasa_ves, fecha_tasa, es_dia_publicado
        FROM marts.fct_tasa_diaria
        ORDER BY fecha
    """
    with conectar() as conn:
        filas = conn.execute(consulta).fetchall()

    df = pd.DataFrame(
        filas, columns=["fecha", "tasa_ves", "fecha_tasa", "es_dia_publicado"]
    )
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["fecha_tasa"] = pd.to_datetime(df["fecha_tasa"])
    df["tasa_ves"] = df["tasa_ves"].astype(float)  # NUMERIC llega como Decimal
    return df


# --- Carga, con mensajes claros si la base todavía no está lista ---
try:
    df = cargar_datos()
except psycopg.errors.UndefinedTable:
    st.info("Todavía no hay datos. Ejecuta el DAG pipeline_tasas_ve en Airflow.")
    st.stop()
except psycopg.OperationalError:
    st.error("No se pudo conectar a la base de datos.")
    st.stop()

if df.empty:
    st.info("La tabla está vacía. Ejecuta el DAG pipeline_tasas_ve en Airflow.")
    st.stop()

st.title("Tasa oficial USD/VES")
st.caption("Fuente: BCV, vía DolarAPI. Pipeline: Airflow, dbt y PostgreSQL.")

# --- Indicadores ---
# "Hoy" en Caracas, porque el contenedor trabaja en UTC y de noche
# estaría un día adelantado.
hoy = pd.Timestamp(datetime.now(ZoneInfo("America/Caracas")).date())

vigente = df[df["fecha"] <= hoy].iloc[-1]  # última fecha que ya rige
futuras = df[(df["fecha"] > hoy) & df["es_dia_publicado"]]  # publicadas por adelantado

delta = None
hace_30 = df[df["fecha"] == vigente["fecha"] - pd.Timedelta(days=30)]
if not hace_30.empty:
    cambio = (vigente["tasa_ves"] / hace_30.iloc[0]["tasa_ves"] - 1) * 100
    delta = f"{cambio:+.1f}% en 30 días"

col1, col2, col3 = st.columns(3)
col1.metric(
    f"Tasa vigente ({vigente['fecha'].date()})",
    f"{vigente['tasa_ves']:,.4f} Bs/USD",
    delta=delta,
    delta_color="off",  # que suba una tasa no es "bueno" ni "malo"
)
if futuras.empty:
    col2.metric("Publicada para el próximo día", "sin dato")
else:
    proxima = futuras.iloc[0]
    col2.metric(
        f"Publicada para el {proxima['fecha'].date()}",
        f"{proxima['tasa_ves']:,.4f} Bs/USD",
    )
publicados = int(df["es_dia_publicado"].sum())
col3.metric(
    "Días publicados / total",
    f"{publicados:,} / {len(df):,}",
    delta=f"{len(df) - publicados:,} rellenados",
    delta_color="off",
)

# --- Filtros ---
fmin, fmax = df["fecha"].min().date(), df["fecha"].max().date()
rango = st.sidebar.slider(
    "Rango de fechas", min_value=fmin, max_value=fmax, value=(fmin, fmax)
)
escala_log = st.sidebar.checkbox("Escala logarítmica", value=True)
st.sidebar.caption(
    "La tasa pasó de unos 17 a unos 887 Bs/USD en tres años. En escala normal "
    "los primeros años se ven planos; la logarítmica deja ver los cambios "
    "relativos en todo el período."
)
vista = df[(df["fecha"].dt.date >= rango[0]) & (df["fecha"].dt.date <= rango[1])]

# --- Serie diaria ---
st.subheader("Serie diaria")
fig = go.Figure()
fig.add_trace(
    go.Scatter(x=vista["fecha"], y=vista["tasa_ves"], mode="lines", name="Tasa")
)
# Puntos encima de los días en que la tasa fue rellenada (sin publicación del BCV).
rellenados = vista[~vista["es_dia_publicado"]]
fig.add_trace(
    go.Scatter(
        x=rellenados["fecha"],
        y=rellenados["tasa_ves"],
        mode="markers",
        name="Día rellenado",
        marker=dict(size=4, color="orange"),
    )
)
fig.update_yaxes(type="log" if escala_log else "linear", title="Bs por USD")
fig.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
st.plotly_chart(fig)
st.caption(
    "Los puntos naranja son sábados, domingos, feriados y días sin publicación: "
    "toman la última tasa publicada."
)

# --- Variación mensual ---
st.subheader("Variación mensual (%)")
# Último valor de cada mes contra el del mes anterior.
mensual = vista.set_index("fecha")["tasa_ves"].resample("MS").last()
variacion = mensual.pct_change().dropna() * 100
fig2 = go.Figure(go.Bar(x=variacion.index, y=variacion.values))
fig2.update_yaxes(title="%")
fig2.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig2)

# --- Calidad de datos ---
st.subheader("Calidad de datos: días hábiles sin tasa publicada")
# dayofweek < 5 son lunes a viernes. Si no hay tasa en un día así,
# es un feriado o un hueco de la fuente.
sin_dato = df[(~df["es_dia_publicado"]) & (df["fecha"].dt.dayofweek < 5)]
st.write(
    f"{len(sin_dato)} días hábiles (lunes a viernes) sin tasa publicada. "
    "Pueden ser feriados o huecos de la fuente. Los 15 más recientes:"
)
tabla = sin_dato.sort_values("fecha", ascending=False).head(15).copy()
tabla["día"] = tabla["fecha"].dt.dayofweek.map(lambda i: DIAS[i])
tabla["fecha"] = tabla["fecha"].dt.date
tabla["tasa tomada del"] = tabla["fecha_tasa"].dt.date
tabla = tabla.rename(columns={"tasa_ves": "tasa usada"})
st.dataframe(tabla[["fecha", "día", "tasa usada", "tasa tomada del"]], hide_index=True)