"""Análisis exploratorio de datos (EDA) y calidad de datos: python -m src.eda
Lee todos los crudos de data/raw y el histórico de SQLite. Genera en data/reportes/eda/:
figuras PNG, eda_tablas.xlsx y metricas.json (insumo del informe de la Entrega 2)."""
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import config
from src.transform.limpieza import limpiar, agregar_variantes, UMBRAL_DESCUENTO_SOSPECHOSO
from src.transform.emparejar import agregar_clave, productos_comparables

DESTINO = config.DIR_REPORTES / "eda"
TIENDAS = ["Alkosto", "Alkomprar", "Exito", "Falabella"]
# Alkosto y Alkomprar son del mismo grupo: misma familia de color
COLOR = {"Alkosto": "#1f3a5f", "Alkomprar": "#6f93bf", "Exito": "#c9a227", "Falabella": "#3a8d5d"}
ACENTO = "#c0392b"
FUENTES = {
    "Alkosto": ("alkosto.com/search?text=", "HTML renderizado (Hybris + Algolia)"),
    "Alkomprar": ("alkomprar.com/search?text=", "HTML renderizado (Hybris + Algolia)"),
    "Exito": ("exito.com/s?q=", "HTML renderizado (VTEX FastStore)"),
    "Falabella": ("falabella.com.co/.../search?Ntt=", "JSON embebido (__NEXT_DATA__)"),
}

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .3, "axes.axisbelow": True})


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(DESTINO / nombre, dpi=160)
    plt.close(fig)


def cargar_crudos() -> pd.DataFrame:
    partes = []
    for ruta in sorted(config.DIR_RAW.glob("ofertas_raw_*.csv")):
        df = pd.read_csv(ruta, dtype={"ean": str})
        df["fecha"] = ruta.stem.replace("ofertas_raw_", "")
        if "categoria" not in df:
            df["categoria"] = "celular"
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


def procesar(raw: pd.DataFrame):
    """Aplica el mismo T del pipeline por fecha, para medir cada etapa del embudo."""
    limpias, agrupadas = [], []
    for fecha, g in raw.groupby("fecha"):
        lim = limpiar(g)
        lim["fecha"] = fecha
        limpias.append(lim)
        agr = agregar_clave(agregar_variantes(lim))
        agregadas = agr.assign(fecha=fecha)
        agrupadas.append(agregadas)
    return pd.concat(limpias, ignore_index=True), pd.concat(agrupadas, ignore_index=True)


def comparables_por_fecha(agrupadas):
    base = agrupadas[(agrupadas.condicion == "nuevo") & (agrupadas.tipo_vendedor == "tienda")]
    return pd.concat([productos_comparables(g) for _, g in base.groupby("fecha")], ignore_index=True)


def tabla_brechas(comp):
    """Por producto y fecha: precio mínimo, máximo y brecha entre tiendas."""
    g = comp.groupby(["fecha", "categoria", "producto_id"])
    t = g["precio_actual"].agg(["min", "max", "count"]).rename(columns={"count": "n_tiendas"})
    t["brecha_pct"] = (t["max"] - t["min"]) / t["max"] * 100
    t["ahorro_cop"] = t["max"] - t["min"]
    return t.reset_index()


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    raw = cargar_crudos()
    limpias, agrupadas = procesar(raw)
    comp = comparables_por_fecha(agrupadas)
    fechas = sorted(raw["fecha"].unique())
    ult = fechas[-1]
    M = {"fechas": fechas, "ultima_fecha": ult}

    # ------------------------------------------------------------ 1.1 Estructura de las fuentes
    r_ult = raw[raw.fecha == ult]
    estructura = (raw.groupby(["tienda"]).agg(registros_crudos=("nombre", "size"))
                  .join(r_ult.groupby(["tienda", "categoria"]).size().unstack(fill_value=0).add_prefix("crudos_ult_"))
                  .reindex(TIENDAS))
    estructura["acceso"] = [FUENTES[t][1] for t in estructura.index]
    estructura["publica_ean"] = [bool(raw.loc[raw.tienda == t, "ean"].notna().any()) for t in estructura.index]
    M["crudos_por_fecha"] = raw.groupby(["fecha", "categoria"]).size().unstack(fill_value=0).to_dict("index")
    M["crudos_total"] = int(len(raw))
    M["estructura"] = estructura.reset_index().to_dict("records")

    # ------------------------------------------------------------ Duplicados y solapamiento de catálogo
    dup = r_ult.groupby("tienda").apply(lambda g: g.duplicated(["url", "precio_actual"]).sum(), include_groups=False)
    M["duplicados_ult"] = {t: int(dup.get(t, 0)) for t in TIENDAS}
    M["duplicados_pct_ult"] = {t: round(dup.get(t, 0) / max(1, (r_ult.tienda == t).sum()) * 100, 1) for t in TIENDAS}
    ak = r_ult[r_ult.tienda == "Alkosto"].dropna(subset=["ean"]).drop_duplicates("ean").set_index("ean")["precio_actual"]
    km = r_ult[r_ult.tienda == "Alkomprar"].dropna(subset=["ean"]).drop_duplicates("ean").set_index("ean")["precio_actual"]
    comunes = ak.index.intersection(km.index)
    M["alk_ean_comunes"] = int(len(comunes))
    M["alk_ean_union"] = int(len(ak.index.union(km.index)))
    M["alk_solape_pct"] = round(len(comunes) / max(1, M["alk_ean_union"]) * 100, 1)
    M["alk_mismo_precio_pct"] = round((ak[comunes] == km[comunes]).mean() * 100, 1) if len(comunes) else None

    # ------------------------------------------------------------ Embudo de calidad (última fecha)
    l_ult, a_ult, c_ult = limpias[limpias.fecha == ult], agrupadas[agrupadas.fecha == ult], comp[comp.fecha == ult]
    homolog = l_ult.dropna(subset=["marca", "modelo", "variante"])
    embudo = pd.DataFrame({
        "crudas": r_ult.groupby("tienda").size(),
        "validas": l_ult.groupby("tienda").size(),
        "homologadas": homolog.groupby("tienda").size(),
        "unicas_sin_color": a_ult.groupby("tienda").size(),
        "comparables": c_ult.groupby("tienda").size(),
    }).reindex(TIENDAS).fillna(0).astype(int)
    M["embudo"] = embudo.to_dict("index")
    M["embudo_total"] = embudo.sum().to_dict()

    # % no homologable (sin marca/modelo/variante) por tienda y categoría: equivalente a "faltantes" del problema
    l_ult = l_ult.assign(no_homologable=l_ult[["marca", "modelo", "variante"]].isna().any(axis=1))
    no_hom = (l_ult.groupby(["tienda", "categoria"])["no_homologable"].mean().unstack() * 100).reindex(TIENDAS)
    M["no_homologable_pct"] = no_hom.round(1).to_dict("index")
    M["no_homologable_global_pct"] = round(l_ult["no_homologable"].mean() * 100, 1)
    faltante_attr = (l_ult.groupby("categoria")[["marca", "modelo", "variante"]].apply(lambda g: g.isna().mean() * 100)
                     .round(1))
    M["faltante_atributo_pct"] = faltante_attr.to_dict("index")
    M["ean_faltante_pct"] = (r_ult.groupby("tienda")["ean"].apply(lambda s: s.isna().mean() * 100)
                             .reindex(TIENDAS).round(1).to_dict())

    # Faltantes en campos crudos por tienda (ausencia estructural: la tienda no publica el campo en el listado)
    cols_raw = ["nombre", "marca_tienda", "ean", "precio_actual", "precio_original", "vendedor", "url"]
    falt_raw = (r_ult.replace({"": np.nan}).groupby("tienda")[cols_raw]
                .apply(lambda g: g.isna().mean() * 100).reindex(TIENDAS).round(1))
    M["faltante_crudo_pct"] = falt_raw.to_dict("index")
    M["faltante_crudo_global_pct"] = round(float(r_ult[cols_raw].replace({"": np.nan}).isna().mean().mean() * 100), 1)

    # Ausencia de productos: sobre el catálogo homologado (nuevo, vendedor tienda), % de productos que cada tienda NO tiene
    cat_base = a_ult[(a_ult.condicion == "nuevo") & (a_ult.tipo_vendedor == "tienda")]
    presencia = (cat_base.assign(v=1).pivot_table(index=["categoria", "producto_id"], columns="tienda", values="v",
                                                  aggfunc="max").reindex(columns=TIENDAS).fillna(0).astype(int))
    ausencia = (1 - presencia.groupby(level="categoria").mean()) * 100
    M["catalogo_homologado"] = presencia.groupby(level="categoria").size().to_dict()
    M["ausencia_pct"] = ausencia.round(1).to_dict("index")
    n_t = presencia.sum(axis=1)
    M["productos_por_n_tiendas"] = n_t.groupby(level="categoria").value_counts().unstack(fill_value=0).to_dict("index")
    M["ausencia_global_pct"] = round(float((1 - presencia.values.mean()) * 100), 1)
    M["solo_una_tienda_pct"] = (n_t.eq(1).groupby(level="categoria").mean() * 100).round(1).to_dict()

    # Composición: marketplace, reacondicionados, combos
    comp_t = l_ult.groupby("tienda").agg(
        n=("nombre", "size"),
        marketplace_pct=("tipo_vendedor", lambda s: (s == "marketplace").mean() * 100),
        reacondicionado_pct=("condicion", lambda s: (s == "reacondicionado").mean() * 100),
    ).reindex(TIENDAS).round(1)
    M["composicion"] = comp_t.to_dict("index")
    tv = l_ult[l_ult.categoria == "televisor"]
    M["combos_tv"] = int(tv["combo"].sum()) if len(tv) else 0
    M["combos_tv_pct"] = round(tv["combo"].mean() * 100, 1) if len(tv) else 0

    # ------------------------------------------------------------ 1.2 Estadísticas descriptivas
    nuevos = l_ult[l_ult.condicion == "nuevo"]
    desc = (nuevos.groupby(["categoria", "tienda"])["precio_actual"]
            .agg(n="size", media="mean", desv="std", minimo="min", mediana="median", maximo="max"))
    desc["cv_pct"] = desc["desv"] / desc["media"] * 100
    M["descriptivas"] = [{"categoria": c, "tienda": t, **{k: float(v) for k, v in fila.items()}}
                         for (c, t), fila in desc.iterrows()]

    # Descuento publicado y sospechosos
    dsc = nuevos.groupby("tienda").agg(
        con_descuento_pct=("descuento_pct", lambda s: (s > 0.5).mean() * 100),
        descuento_mediano=("descuento_pct", lambda s: s[s > 0.5].median()),
        sospechosos=("descuento_sospechoso", "sum"),
        sospechosos_pct=("descuento_sospechoso", lambda s: s.mean() * 100),
    ).reindex(TIENDAS).round(1)
    M["descuentos"] = dsc.to_dict("index")
    M["descuento_umbral"] = UMBRAL_DESCUENTO_SOSPECHOSO
    ejemplos = nuevos[nuevos.descuento_sospechoso].sort_values("descuento_pct", ascending=False)
    M["ejemplos_sospechosos"] = ejemplos.head(5)[["tienda", "nombre", "precio_original", "precio_actual",
                                                  "descuento_pct"]].to_dict("records")

    # Outliers de precio dentro de cada (categoría, marca) por IQR
    def iqr_flag(s):
        q1, q3 = s.quantile([.25, .75])
        return (s < q1 - 1.5 * (q3 - q1)) | (s > q3 + 1.5 * (q3 - q1))
    nuevos = nuevos.assign(outlier=nuevos.groupby(["categoria", "marca"])["precio_actual"].transform(iqr_flag))
    M["outliers_iqr"] = int(nuevos["outlier"].sum())
    M["outliers_iqr_pct"] = round(nuevos["outlier"].mean() * 100, 1)

    # ------------------------------------------------------------ 1.3 Brechas entre tiendas y patrones temporales
    br = tabla_brechas(comp)
    br_ult = br[br.fecha == ult]
    M["comparables_ult"] = br_ult.groupby("categoria").size().to_dict()
    M["brecha_ult"] = br_ult.groupby("categoria")["brecha_pct"].describe().round(1).to_dict("index")
    M["brecha_cero_pct"] = br_ult.groupby("categoria")["brecha_pct"].apply(lambda s: (s < 0.5).mean() * 100).round(1).to_dict()
    M["brecha_mayor_10_pct"] = br_ult.groupby("categoria")["brecha_pct"].apply(lambda s: (s >= 10).mean() * 100).round(1).to_dict()
    M["ahorro_ult"] = br_ult.groupby("categoria")["ahorro_cop"].agg(["median", "max"]).round(0).to_dict("index")
    # Alkosto y Alkomprar son el mismo grupo comercial: un producto solo en ambas no es una comparación de mercado
    grupos = c_ult.assign(grupo=c_ult.tienda.replace({"Alkomprar": "Alkosto"})).groupby("producto_id")["grupo"].nunique()
    br_ult = br_ult.assign(n_grupos=br_ult.producto_id.map(grupos))
    solo_alk = br_ult[br_ult.n_grupos < 2]
    M["comparables_solo_grupo_alk"] = solo_alk.groupby("categoria").size().to_dict()
    M["comparables_multigrupo"] = br_ult[br_ult.n_grupos >= 2].groupby("categoria").size().to_dict()
    M["brecha_multigrupo"] = (br_ult[br_ult.n_grupos >= 2].groupby("categoria")["brecha_pct"]
                              .describe().round(1).to_dict("index"))
    M["ahorro_multigrupo"] = (br_ult[br_ult.n_grupos >= 2].groupby("categoria")["ahorro_cop"]
                              .agg(["median", "mean", "max"]).round(0).to_dict("index"))
    M["brecha_solo_alk_cero_pct"] = round((solo_alk["brecha_pct"] < 0.5).mean() * 100, 1) if len(solo_alk) else None
    top = br_ult.sort_values("ahorro_cop", ascending=False).head(8)
    M["top_ahorro"] = top[["categoria", "producto_id", "min", "max", "ahorro_cop", "brecha_pct", "n_tiendas", "n_grupos"]].to_dict("records")

    # Tienda más barata (sin contar empates de Alkosto/Alkomprar como dos victorias independientes)
    minimos = c_ult.merge(br_ult[["producto_id", "min"]], on="producto_id")
    ganadoras = minimos[minimos.precio_actual == minimos["min"]]
    M["veces_mas_barata"] = (ganadoras.groupby(["categoria", "tienda"]).size().unstack(fill_value=0)
                             .reindex(columns=TIENDAS, fill_value=0).to_dict("index"))
    M["presencia_comparables"] = (c_ult.groupby(["categoria", "tienda"]).size().unstack(fill_value=0)
                                  .reindex(columns=TIENDAS, fill_value=0).to_dict("index"))

    # Cambios de precio entre fechas (mismo producto, tienda y vendedor)
    base_h = agrupadas[(agrupadas.condicion == "nuevo") & (agrupadas.tipo_vendedor == "tienda")]
    M["cambios"] = None
    if len(fechas) >= 2:
        f0, f1 = fechas[-2], fechas[-1]
        k = ["tienda", "producto_id"]
        a0 = base_h[base_h.fecha == f0].set_index(k)["precio_actual"]
        a1 = base_h[base_h.fecha == f1].set_index(k)["precio_actual"]
        comunes_h = a0.index.intersection(a1.index)
        var = ((a1[comunes_h] - a0[comunes_h]) / a0[comunes_h] * 100)
        cambios = var.groupby(level="tienda").agg(
            n="size", cambiaron_pct=lambda s: (s.abs() > 0.1).mean() * 100,
            var_media_pct=lambda s: s[s.abs() > 0.1].mean(), subieron=lambda s: (s > 0.1).sum(),
            bajaron=lambda s: (s < -0.1).sum()).reindex(TIENDAS).round(1)
        M["cambios"] = {"desde": f0, "hasta": f1, "n_total": int(len(var)),
                        "cambiaron_pct_total": round((var.abs() > 0.1).mean() * 100, 1),
                        "por_tienda": cambios.to_dict("index"),
                        "max_subida_pct": round(float(var.max()), 1), "max_bajada_pct": round(float(var.min()), 1)}
        # Rotación del surtido: productos que aparecen/desaparecen entre fechas (solo celulares, presentes en ambas)
        cel0 = set(base_h[(base_h.fecha == f0) & (base_h.categoria == "celular")]["producto_id"])
        cel1 = set(base_h[(base_h.fecha == f1) & (base_h.categoria == "celular")]["producto_id"])
        M["rotacion_celulares"] = {"f0": len(cel0), "f1": len(cel1), "comunes": len(cel0 & cel1),
                                   "jaccard_pct": round(len(cel0 & cel1) / max(1, len(cel0 | cel1)) * 100, 1)}
    else:
        var = pd.Series(dtype=float)

    # Correlación simple en celulares: precio vs almacenamiento
    cel = nuevos[(nuevos.categoria == "celular")].dropna(subset=["almacenamiento_gb"])
    M["corr_precio_almacenamiento"] = round(float(np.corrcoef(np.log2(cel.almacenamiento_gb.astype(float)),
                                                              np.log(cel.precio_actual))[0, 1]), 2) if len(cel) > 2 else None
    tvs = nuevos[(nuevos.categoria == "televisor")].dropna(subset=["pulgadas"])
    M["corr_precio_pulgadas"] = round(float(np.corrcoef(tvs.pulgadas.astype(float), np.log(tvs.precio_actual.astype(float)))[0, 1]), 2) if len(tvs) > 2 else None

    # ============================================================ FIGURAS
    def mapa_calor(ax, tabla, titulo, vmax=100):
        im = ax.imshow(tabla.values.astype(float), cmap="Reds", vmin=0, vmax=vmax, aspect="auto")
        ax.set_xticks(range(tabla.shape[1]), tabla.columns, rotation=30, ha="right")
        ax.set_yticks(range(len(tabla)), tabla.index)
        ax.grid(False)
        for i in range(tabla.shape[0]):
            for j in range(tabla.shape[1]):
                v = float(tabla.values[i, j])
                ax.text(j, i, "—" if np.isnan(v) else f"{v:.0f}%", ha="center", va="center", fontsize=8.5,
                        color="white" if v > vmax * .55 else "black")
        ax.set_title(titulo)
        return im

    # Fig 1: faltantes en campos crudos + % no homologable
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.4), gridspec_kw={"width_ratios": [1.7, 1]})
    mapa_calor(ax[0], falt_raw, f"% de faltantes por campo en el dato crudo ({ult})")
    im = mapa_calor(ax[1], no_hom.rename(columns=str.capitalize),
                    "% de ofertas válidas no homologables\n(sin marca, modelo o variante)")
    fig.colorbar(im, ax=ax[1], fraction=.05)
    guardar(fig, "fig1_faltantes.png")

    # Fig 2: ausencia de productos por tienda + embudo de calidad
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.5), gridspec_kw={"width_ratios": [1, 1.4]})
    cats_a = list(ausencia.index)
    x = np.arange(len(TIENDAS))
    w = .38
    for k, (cat, col) in enumerate(zip(cats_a, ["#1f3a5f", "#c9a227"])):
        barras = ax[0].bar(x + (k - (len(cats_a) - 1) / 2) * w, ausencia.loc[cat, TIENDAS], w, color=col,
                           label=f"{cat} (catálogo={M['catalogo_homologado'][cat]})")
        ax[0].bar_label(barras, fmt="%.0f%%", fontsize=7.5)
    ax[0].set_xticks(x, TIENDAS)
    ax[0].set_ylim(0, 100)
    ax[0].set_ylabel("% del catálogo homologado ausente")
    ax[0].set_title("Productos que cada tienda NO ofrece")
    ax[0].legend(fontsize=7.5, frameon=False, loc="upper left")
    etapas = ["crudas", "validas", "homologadas", "unicas_sin_color", "comparables"]
    etiquetas = ["Crudas", "Válidas", "Homologadas", "Únicas\n(sin color)", "Comparables\n(≥2 tiendas)"]
    x = np.arange(len(etapas))
    w = .2
    for i, t in enumerate(TIENDAS):
        ax[1].bar(x + (i - 1.5) * w, embudo.loc[t, etapas], w, label=t, color=COLOR[t])
    ax[1].set_xticks(x, etiquetas)
    ax[1].set_ylabel("Ofertas")
    ax[1].set_title(f"Embudo de calidad por tienda ({ult})")
    ax[1].legend(ncols=2, fontsize=7.5, frameon=False)
    guardar(fig, "fig2_ausencia_embudo.png")

    # Fig 3: en cuántas tiendas aparece cada producto + superposición de catálogo entre pares de tiendas
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.3), gridspec_kw={"width_ratios": [1.1, 1]})
    dist = n_t.groupby(level="categoria").value_counts(normalize=True).unstack(fill_value=0).reindex(
        columns=[1, 2, 3, 4], fill_value=0) * 100
    x = np.arange(4)
    for k, (cat, col) in enumerate(zip(dist.index, ["#1f3a5f", "#c9a227"])):
        b_ = ax[0].bar(x + (k - .5) * .38, dist.loc[cat], .38, color=col, label=cat)
        ax[0].bar_label(b_, fmt="%.0f%%", fontsize=7.5)
    ax[0].set_xticks(x, ["1 tienda", "2 tiendas", "3 tiendas", "4 tiendas"])
    ax[0].set_ylabel("% del catálogo homologado")
    ax[0].set_title("¿En cuántas tiendas está cada producto?")
    ax[0].legend(frameon=False, fontsize=8)
    # solape[A, B] = % de los productos de A que también ofrece B
    solape = pd.DataFrame({b: [(presencia[a_] & presencia[b]).sum() / max(1, presencia[a_].sum()) * 100
                                for a_ in TIENDAS] for b in TIENDAS}, index=TIENDAS)
    M["solape_catalogo_pct"] = solape.round(1).to_dict("index")
    mapa_calor(ax[1], solape.where(~np.eye(4, dtype=bool)), "% del catálogo de la fila que\ntambién ofrece la columna")
    guardar(fig, "fig3_presencia.png")

    # Fig 2: distribución de precios por tienda y categoría + descuentos publicados
    cats = [c for c in config.CATEGORIAS if c in nuevos.categoria.unique()]
    fig, ax = plt.subplots(1, len(cats) + 1, figsize=(11, 3.6))
    for a_, cat in zip(ax, cats):
        datos = [nuevos[(nuevos.categoria == cat) & (nuevos.tienda == t)]["precio_actual"] / 1e6 for t in TIENDAS]
        bp = a_.boxplot(datos, tick_labels=TIENDAS, patch_artist=True, widths=.6,
                        medianprops={"color": ACENTO}, flierprops={"markersize": 3, "alpha": .5})
        for caja, t in zip(bp["boxes"], TIENDAS):
            caja.set_facecolor(COLOR[t])
            caja.set_alpha(.75)
        a_.set_yscale("log")
        a_.set_title(f"Precio actual: {'celulares' if cat == 'celular' else 'televisores'} nuevos")
        a_.set_ylabel("Millones COP (escala log)")
        a_.tick_params(axis="x", labelsize=8)
    con_d = nuevos[nuevos.descuento_pct > 0.5]
    bins = np.arange(0, 101, 5)
    ax[-1].hist([con_d[con_d.tienda == t]["descuento_pct"] for t in TIENDAS], bins=bins, stacked=True,
                color=[COLOR[t] for t in TIENDAS], label=TIENDAS)
    ax[-1].axvline(UMBRAL_DESCUENTO_SOSPECHOSO, color=ACENTO, ls="--", lw=1.2)
    ax[-1].text(UMBRAL_DESCUENTO_SOSPECHOSO + 1, ax[-1].get_ylim()[1] * .85, "sospechoso\n(>60%)", color=ACENTO,
                fontsize=8)
    ax[-1].set_title("Descuento publicado (ofertas con descuento)")
    ax[-1].set_xlabel("% sobre el precio tachado")
    ax[-1].legend(fontsize=7, frameon=False)
    guardar(fig, "fig4_precios_descuentos.png")

    # Fig 3: brecha entre tiendas para el mismo producto + cambios de precio entre fechas
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.4))
    for cat, col in zip(cats, ["#1f3a5f", "#c9a227"]):
        s = br_ult[(br_ult.categoria == cat) & (br_ult.n_grupos >= 2)]["brecha_pct"]
        ax[0].hist(s, bins=np.arange(0, max(41, s.max() + 2), 2), alpha=.75, color=col, label=f"{cat} (n={len(s)})")
    ax[0].set_title("Brecha de precio del mismo producto entre tiendas\n(productos en ≥2 grupos comerciales)")
    ax[0].set_xlabel("(máx − mín) / máx  (%)")
    ax[0].set_ylabel("Productos comparables")
    ax[0].legend(frameon=False)
    if len(var):
        v = var[var.abs() > 0.1]
        orden = [t for t in TIENDAS if t in v.index.get_level_values("tienda")]
        partes = [v.xs(t, level="tienda") for t in orden]
        ax[1].hist(partes, bins=np.arange(-30, 31, 2.5), stacked=True, color=[COLOR[t] for t in orden], label=orden)
        ax[1].axvline(0, color="black", lw=.8)
        ax[1].set_title(f"Cambio de precio {fechas[-2]} → {fechas[-1]}\n"
                        f"({M['cambios']['cambiaron_pct_total']:.0f}% de {M['cambios']['n_total']} ofertas cambió)")
        ax[1].set_xlabel("Variación (%) — solo ofertas que cambiaron")
        ax[1].legend(fontsize=7, frameon=False)
    else:
        ax[1].text(.5, .5, "Se requiere ≥ 2 fechas", ha="center", transform=ax[1].transAxes)
    guardar(fig, "fig5_brechas_cambios.png")

    # Fig 4: relación precio-atributo (señal que justifica la homologación por atributo)
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.2))
    for t in TIENDAS:
        s = cel[cel.tienda == t]
        ax[0].scatter(s.almacenamiento_gb * np.exp(np.random.default_rng(1).normal(0, .06, len(s))),
                      s.precio_actual / 1e6, s=10, alpha=.5, color=COLOR[t], label=t)
        s = tvs[tvs.tienda == t]
        ax[1].scatter(s.pulgadas.astype(float) + np.random.default_rng(2).normal(0, .6, len(s)), s.precio_actual / 1e6, s=10,
                      alpha=.5, color=COLOR[t], label=t)
    ax[0].set_xscale("log", base=2)
    ax[0].set_yscale("log")
    ax[0].set_xlabel("Almacenamiento (GB)")
    ax[0].set_ylabel("Millones COP (log)")
    ax[0].set_title(f"Celulares: precio vs. almacenamiento (r={M['corr_precio_almacenamiento']})")
    if len(tvs):
        ax[1].set_yscale("log")
    ax[1].set_xlabel("Pulgadas")
    ax[1].set_title(f"Televisores: precio vs. tamaño (r={M['corr_precio_pulgadas']})")
    ax[1].legend(fontsize=7, frameon=False)
    guardar(fig, "fig6_precio_atributos.png")

    # ============================================================ SALIDAS
    with pd.ExcelWriter(DESTINO / "eda_tablas.xlsx") as xl:
        estructura.to_excel(xl, sheet_name="fuentes")
        falt_raw.to_excel(xl, sheet_name="faltantes_crudo_pct")
        ausencia.to_excel(xl, sheet_name="ausencia_productos_pct")
        presencia.to_excel(xl, sheet_name="matriz_presencia")
        embudo.to_excel(xl, sheet_name="embudo")
        no_hom.to_excel(xl, sheet_name="no_homologable_pct")
        desc.round(0).to_excel(xl, sheet_name="descriptivas")
        dsc.to_excel(xl, sheet_name="descuentos")
        ejemplos.to_excel(xl, sheet_name="descuentos_sospechosos", index=False)
        br_ult.sort_values("ahorro_cop", ascending=False).to_excel(xl, sheet_name="brechas", index=False)
        if len(var):
            var.rename("variacion_pct").reset_index().to_excel(xl, sheet_name="cambios_precio", index=False)
    (DESTINO / "metricas.json").write_text(json.dumps(M, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(M, ensure_ascii=False, indent=1, default=str)[:6000])
    print(f"\nSalida en {DESTINO}")


if __name__ == "__main__":
    main()
