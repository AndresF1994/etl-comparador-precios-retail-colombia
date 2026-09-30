"""Transformación (T): limpia ofertas crudas, extrae atributos por categoría y agrega variantes de color."""
import numpy as np
import pandas as pd
from src import config
from . import atributos as a

ES_VALIDO = {"celular": a.es_celular, "televisor": a.es_televisor}
UMBRAL_DESCUENTO_SOSPECHOSO = 60   # % publicado por encima del cual el precio "antes" no es creíble


def _atributos_celular(nombre, marca):
    gb = a.detectar_almacenamiento(nombre)
    return {"modelo": a.detectar_modelo(nombre, marca), "almacenamiento_gb": gb, "ram_gb": a.detectar_ram(nombre),
            "pulgadas": None, "combo": False, "variante": f"{gb}gb" if gb else None}


def _atributos_televisor(nombre, marca):
    pulgadas = a.detectar_pulgadas(nombre)
    combo = a.es_combo(nombre)
    variante = f"{pulgadas}in" + (" +combo" if combo else "") if pulgadas else None
    return {"modelo": a.detectar_modelo_tv(nombre, pulgadas), "almacenamiento_gb": None, "ram_gb": None,
            "pulgadas": pulgadas, "combo": combo, "variante": variante}


def limpiar(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Ofertas crudas -> ofertas limpias con atributos, una fila por oferta válida de la categoría buscada."""
    df = df_raw.copy()
    if "categoria" not in df:
        df["categoria"] = "celular"   # crudos anteriores a la inclusión de televisores
    df["categoria"] = df["categoria"].fillna("celular")
    df = df.dropna(subset=["nombre", "precio_actual"])
    df = df.drop_duplicates(subset=["tienda", "url", "precio_actual"])   # Falabella repite tarjetas patrocinadas
    df = df[[ES_VALIDO[c](n) for c, n in zip(df["categoria"], df["nombre"])]]

    df["marca"] = [a.detectar_marca(n, m) for n, m in zip(df["nombre"], df["marca_tienda"].fillna(""))]
    extra = [(_atributos_celular if c == "celular" else _atributos_televisor)(n, m)
             for c, n, m in zip(df["categoria"], df["nombre"], df["marca"])]
    df = pd.concat([df.reset_index(drop=True), pd.DataFrame(extra)], axis=1)
    df["condicion"] = df["nombre"].map(a.detectar_condicion)
    df["tipo_vendedor"] = (df["vendedor"].str.lower() == df["tienda"].str.lower()).map(
        {True: "tienda", False: "marketplace"})

    df["precio_original"] = df["precio_original"].fillna(df["precio_actual"])
    df["precio_original"] = df[["precio_original", "precio_actual"]].max(axis=1)
    df["descuento_pct"] = (1 - df["precio_actual"] / df["precio_original"]) * 100
    # Un descuento publicado > 60% casi siempre es un precio de lista inflado: se marca y no se usa como descuento real
    df["descuento_sospechoso"] = df["descuento_pct"] > UMBRAL_DESCUENTO_SOSPECHOSO
    df["descuento_pct_valido"] = np.where(df["descuento_sospechoso"], np.nan, df["descuento_pct"])

    # Descarta lecturas fuera del rango razonable de su categoría
    rango = df["categoria"].map(config.RANGO_PRECIO)
    df = df[[lo <= p <= hi for p, (lo, hi) in zip(df["precio_actual"], rango)]]
    return df.reset_index(drop=True)


def agregar_variantes(df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa variantes de color: una fila por (tienda, tipo_vendedor, condición, categoría, marca, modelo, variante),
    conservando la oferta más barata. Solo aplica a filas con modelo y variante identificados."""
    completos = df.dropna(subset=["marca", "modelo", "variante"])
    clave = ["tienda", "tipo_vendedor", "condicion", "categoria", "marca", "modelo", "variante"]
    idx = completos.groupby(clave)["precio_actual"].idxmin()
    return completos.loc[idx].reset_index(drop=True)
