"""Análisis comparativo desde el punto de vista del comprador:
python -m src.analisis [--categoria celular|televisor] [--incluir-marketplace] [--incluir-reacondicionados]"""
import argparse
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import config
from src.load import db
from src.transform.emparejar import productos_comparables


def preparar(df: pd.DataFrame, marketplace: bool, reacondicionados: bool, categoria: str | None = None) -> pd.DataFrame:
    if categoria:
        df = df[df["categoria"] == categoria]
    if not marketplace:
        df = df[df["tipo_vendedor"] == "tienda"]
    if not reacondicionados:
        df = df[df["condicion"] == "nuevo"]
    return productos_comparables(df, min_tiendas=2)


def tabla_comparativa(df: pd.DataFrame) -> pd.DataFrame:
    """Un producto por fila, una tienda por columna (precio actual), con la tienda más barata y el ahorro posible."""
    ancha = df.pivot_table(index="producto_id", columns="tienda", values="precio_actual", aggfunc="min")
    tiendas = list(ancha.columns)
    ancha["precio_min"] = ancha[tiendas].min(axis=1)
    # En empate (ej. Alkosto y Alkomprar comparten catálogo y precio) se listan todas las tiendas más baratas
    ancha["tienda_mas_barata"] = ancha[tiendas].eq(ancha["precio_min"], axis=0).apply(
        lambda fila: " / ".join(fila.index[fila]), axis=1)
    ancha["precio_max"] = ancha[tiendas].max(axis=1)
    ancha["ahorro_cop"] = ancha["precio_max"] - ancha["precio_min"]
    ancha["ahorro_pct"] = ancha["ahorro_cop"] / ancha["precio_max"] * 100
    return ancha.sort_values("ahorro_cop", ascending=False)


def resumen_por_tienda(df: pd.DataFrame, tabla: pd.DataFrame) -> pd.DataFrame:
    tiendas = df["tienda"].unique()
    filas = []
    for t in tiendas:
        propios = df[df["tienda"] == t]
        idx = propios.set_index("producto_id")["precio_actual"]
        indice = (idx / tabla["precio_min"].reindex(idx.index) - 1).mean() * 100   # % sobre el mínimo del mercado
        filas.append({
            "tienda": t,
            "productos_comparables": len(idx),
            "veces_mas_barata": int(tabla["tienda_mas_barata"].str.split(" / ").map(lambda ts: t in ts).sum()),
            "sobreprecio_prom_vs_minimo_pct": round(indice, 2),
            "descuento_prom_pct": round(propios["descuento_pct_valido"].mean(), 2),
            "precio_prom_cop": round(propios["precio_actual"].mean()),
        })
    return pd.DataFrame(filas).sort_values("veces_mas_barata", ascending=False)


def graficos(df: pd.DataFrame, tabla: pd.DataFrame, resumen: pd.DataFrame, destino):
    fig, ejes = plt.subplots(1, 3, figsize=(17, 5))
    resumen.set_index("tienda")["veces_mas_barata"].plot.bar(ax=ejes[0], color="#2a7de1", rot=0)
    ejes[0].set_title("Veces que es la tienda más barata")
    resumen.set_index("tienda")["sobreprecio_prom_vs_minimo_pct"].plot.bar(ax=ejes[1], color="#e1652a", rot=0)
    ejes[1].set_title("Sobreprecio promedio vs. mínimo del mercado (%)")
    resumen.set_index("tienda")["descuento_prom_pct"].plot.bar(ax=ejes[2], color="#2ab27b", rot=0)
    ejes[2].set_title("Descuento promedio publicado, sin sospechosos (%)")
    for ax in ejes:
        ax.set_xlabel("")
    plt.tight_layout()
    plt.savefig(destino / "resumen_tiendas.png", dpi=130)
    plt.close()

    top = tabla.head(15)
    ax = (top["ahorro_cop"] / 1000).sort_values().plot.barh(figsize=(9, 6), color="#7a5af8")
    ax.set_title("Mayor ahorro posible al elegir la tienda correcta (miles de COP)")
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(destino / "top_ahorro.png", dpi=130)
    plt.close()

    cats = sorted(df["categoria"].unique())
    fig, ejes = plt.subplots(1, len(cats), figsize=(8 * len(cats), 5), squeeze=False)
    for ax, cat in zip(ejes[0], cats):
        por_marca = df[df.categoria == cat].groupby(["marca", "tienda"])["precio_actual"].mean().unstack() / 1e6
        por_marca.plot.bar(ax=ax, rot=0)
        ax.set_title(f"Precio promedio por marca y tienda: {cat} (millones COP)")
        ax.set_xlabel("")
    plt.tight_layout()
    plt.savefig(destino / "precio_por_marca.png", dpi=130)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=None)
    ap.add_argument("--categoria", default=None, choices=config.CATEGORIAS)
    ap.add_argument("--incluir-marketplace", action="store_true")
    ap.add_argument("--incluir-reacondicionados", action="store_true")
    args = ap.parse_args()

    df = preparar(db.leer_ofertas(args.fecha), args.incluir_marketplace, args.incluir_reacondicionados, args.categoria)
    if df.empty:
        print("No hay productos comparables en al menos 2 tiendas con esos filtros.")
        return
    tabla = tabla_comparativa(df)
    resumen = resumen_por_tienda(df, tabla)

    config.DIR_REPORTES.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(config.DIR_REPORTES / "reporte_precios.xlsx") as xl:
        tabla.reset_index().to_excel(xl, sheet_name="comparativa", index=False)
        resumen.to_excel(xl, sheet_name="resumen_tiendas", index=False)
        df.to_excel(xl, sheet_name="ofertas", index=False)
    graficos(df, tabla, resumen, config.DIR_REPORTES)

    pd.set_option("display.width", 200)
    print(f"{len(tabla)} productos comparables en {df['tienda'].nunique()} tiendas\n")
    print(resumen.to_string(index=False))
    print("\nTop 10 mayor ahorro posible:")
    print(tabla.head(10).round(0).to_string())
    print(f"\nReportes en {config.DIR_REPORTES}")


if __name__ == "__main__":
    main()
