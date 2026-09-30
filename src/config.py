from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_REPORTES = RAIZ / "data" / "reportes"
RUTA_DB = RAIZ / "data" / "precios.db"

# Navegación (comportamiento de un usuario normal, sin ráfagas)
PAUSA_SEG = 4
TIMEOUT_MS = 60_000
HEADLESS = True
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

# Búsquedas por categoría y marca, con el término que usaría un comprador
BUSQUEDAS = {
    "celular": {
        "Samsung": "celular samsung",
        "Apple": "iphone",
        "Xiaomi": "celular xiaomi",
        "Motorola": "celular motorola",
        "Honor": "celular honor",
        "Infinix": "celular infinix",
        "Tecno": "celular tecno",
        "Oppo": "celular oppo",
        "Realme": "celular realme",
        "ZTE": "celular zte",
    },
    "televisor": {
        "Samsung": "televisor samsung",
        "LG": "televisor lg",
        "TCL": "televisor tcl",
        "Hisense": "televisor hisense",
        "Kalley": "televisor kalley",
        "Challenger": "televisor challenger",
        "Sony": "televisor sony",
        "Xiaomi": "televisor xiaomi",
    },
}
CATEGORIAS = list(BUSQUEDAS)
MARCAS = sorted({m for marcas in BUSQUEDAS.values() for m in marcas})

# Sinónimos de marca (submarcas) -> marca canónica
ALIAS_MARCA = {
    "samsung": "Samsung", "galaxy": "Samsung",
    "apple": "Apple", "iphone": "Apple",
    "xiaomi": "Xiaomi", "redmi": "Xiaomi", "poco": "Xiaomi",
    "motorola": "Motorola", "moto": "Motorola",
    "honor": "Honor",
    "infinix": "Infinix",
    "tecno": "Tecno",
    "oppo": "Oppo",
    "realme": "Realme",
    "zte": "ZTE", "nubia": "ZTE",
    "lg": "LG", "tcl": "TCL", "hisense": "Hisense", "kalley": "Kalley", "challenger": "Challenger",
    "sony": "Sony", "bravia": "Sony",
}

# Rango de precios razonable por categoría en COP (descarta errores de lectura)
RANGO_PRECIO = {
    "celular": (100_000, 12_000_000),
    "televisor": (300_000, 40_000_000),
}
