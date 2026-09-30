"""Emparejamiento: identifica el mismo producto entre tiendas mediante una clave canónica."""
import pandas as pd


def agregar_clave(df: pd.DataFrame) -> pd.DataFrame:
    """Clave = categoría | marca | modelo | variante. Dos ofertas con la misma clave se consideran el mismo producto.
    Variante: almacenamiento en celulares ('256gb'); pulgadas y combo en televisores ('65in', '65in +combo').
    El color se ignora a propósito: un comprador lo elige después."""
    df = df.copy()
    df["producto_id"] = (df["categoria"] + " | " + df["marca"].str.lower() + " | " + df["modelo"] + " | "
                         + df["variante"])
    return df


def productos_comparables(df: pd.DataFrame, min_tiendas: int = 2) -> pd.DataFrame:
    """Deja solo productos presentes en al menos `min_tiendas` tiendas distintas."""
    n_tiendas = df.groupby("producto_id")["tienda"].nunique()
    validos = n_tiendas[n_tiendas >= min_tiendas].index
    return df[df["producto_id"].isin(validos)].reset_index(drop=True)
