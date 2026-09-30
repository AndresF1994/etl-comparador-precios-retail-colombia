"""Orquestador ETL:
python -m src.pipeline [--categorias celular televisor] [--marcas Samsung LG] [--tiendas Alkosto Exito]
python -m src.pipeline --solo-transformar [--fecha 2026-09-28]   (reprocesa un crudo guardado sin navegar)"""
import argparse
import time
from datetime import date
import pandas as pd

from src import config
from src.extract.base import CAMPOS_OFERTA
from src.extract.alkosto import Alkosto, Alkomprar
from src.extract.exito import Exito
from src.extract.falabella import Falabella
from src.transform.limpieza import limpiar, agregar_variantes
from src.transform.emparejar import agregar_clave
from src.load import db

EXTRACTORES = {e.tienda: e for e in (Alkosto(), Alkomprar(), Exito(), Falabella())}


def extraer(categorias, marcas, tiendas) -> pd.DataFrame:
    """E: navega como usuario (búsqueda por categoría y marca en cada tienda) y devuelve las ofertas crudas."""
    from playwright.sync_api import sync_playwright
    filas = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        ctx = browser.new_context(locale="es-CO", user_agent=config.USER_AGENT)
        page = ctx.new_page()
        page.set_default_timeout(config.TIMEOUT_MS)
        for categoria in categorias:
            for marca, termino in config.BUSQUEDAS[categoria].items():
                if marcas and marca not in marcas:
                    continue
                for nombre_tienda in tiendas:
                    ext = EXTRACTORES[nombre_tienda]
                    try:
                        ofertas = ext.extraer(page, termino, marca)
                        print(f"[E] {nombre_tienda:10} {termino:22} -> {len(ofertas)} ofertas", flush=True)
                    except Exception as e:
                        ofertas = []
                        print(f"[E] {nombre_tienda:10} {termino:22} -> ERROR {type(e).__name__}: {str(e)[:80]}",
                              flush=True)
                    for o in ofertas:
                        o["categoria"] = categoria
                    filas.extend(ofertas)
                    time.sleep(config.PAUSA_SEG)
        browser.close()
    return pd.DataFrame(filas, columns=CAMPOS_OFERTA)


def transformar_y_cargar(raw: pd.DataFrame, fecha: str) -> pd.DataFrame:
    limpias = limpiar(raw)
    con_clave = agregar_clave(agregar_variantes(limpias)) if len(limpias) else limpias
    print(f"[T] {len(limpias)} ofertas válidas, {len(con_clave)} tras agrupar colores")
    sin_modelo = limpias[limpias["modelo"].isna() | limpias["variante"].isna()]
    print(f"[T] {len(sin_modelo)} ofertas sin modelo/variante identificado (no comparables)")
    n = db.guardar_ofertas(con_clave, fecha)
    print(f"[L] {n} ofertas guardadas en {config.RUTA_DB.name} (fecha {fecha})")
    return con_clave


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--categorias", nargs="+", default=config.CATEGORIAS, choices=config.CATEGORIAS)
    ap.add_argument("--marcas", nargs="+", default=None, choices=config.MARCAS)
    ap.add_argument("--tiendas", nargs="+", default=list(EXTRACTORES), choices=list(EXTRACTORES))
    ap.add_argument("--solo-transformar", action="store_true", help="reusa un crudo guardado sin navegar")
    ap.add_argument("--fecha", default=date.today().isoformat(), help="fecha del crudo (AAAA-MM-DD)")
    args = ap.parse_args()

    config.DIR_RAW.mkdir(parents=True, exist_ok=True)
    ruta_raw = config.DIR_RAW / f"ofertas_raw_{args.fecha}.csv"

    if args.solo_transformar:
        raw = pd.read_csv(ruta_raw, dtype={"ean": str})
    else:
        raw = extraer(args.categorias, args.marcas, args.tiendas)
        raw.to_csv(ruta_raw, index=False)
    print(f"[E] {len(raw)} ofertas crudas -> {ruta_raw.name}")
    transformar_y_cargar(raw, args.fecha)


if __name__ == "__main__":
    main()
