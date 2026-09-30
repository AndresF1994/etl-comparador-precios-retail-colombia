"""Carga (L): guarda las ofertas en SQLite conservando el histórico por fecha de extracción."""
import sqlite3
import pandas as pd
from src import config

TABLA_OFERTAS = "ofertas"


def _conexion():
    config.RUTA_DB.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(config.RUTA_DB)


def guardar_ofertas(df: pd.DataFrame, fecha: str) -> int:
    """Inserta las ofertas del día. Es idempotente: si se vuelve a correr el mismo día, reemplaza ese día."""
    df = df.copy()
    df["fecha"] = fecha
    with _conexion() as con:
        existe = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                             (TABLA_OFERTAS,)).fetchone()
        if existe:
            con.execute(f"DELETE FROM {TABLA_OFERTAS} WHERE fecha = ?", (fecha,))
            # Evolución del esquema: agrega columnas nuevas (ej. categoria, pulgadas) sin perder el histórico
            actuales = {fila[1] for fila in con.execute(f"PRAGMA table_info({TABLA_OFERTAS})")}
            for col in df.columns.difference(list(actuales)):
                con.execute(f'ALTER TABLE {TABLA_OFERTAS} ADD COLUMN "{col}"')
        df.to_sql(TABLA_OFERTAS, con, if_exists="append", index=False)
    return len(df)


def leer_ofertas(fecha: str | None = None) -> pd.DataFrame:
    """Lee las ofertas de una fecha (por defecto, la más reciente)."""
    with _conexion() as con:
        if fecha is None:
            fecha = con.execute(f"SELECT MAX(fecha) FROM {TABLA_OFERTAS}").fetchone()[0]
        return pd.read_sql(f"SELECT * FROM {TABLA_OFERTAS} WHERE fecha = ?", con, params=(fecha,))


def leer_historico() -> pd.DataFrame:
    with _conexion() as con:
        return pd.read_sql(f"SELECT * FROM {TABLA_OFERTAS}", con)
