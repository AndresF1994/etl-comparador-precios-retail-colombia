"""Extracción de atributos (marca, modelo, almacenamiento, RAM, condición) desde el nombre del producto."""
import re
import unicodedata
from src import config


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos raros."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+ ]", " ", t.lower())).strip()


COLORES = ("negro|blanco|azul|verde|rojo|rosa|rosado|morado|lila|lavanda|gris|plata|plateado|dorado|oro|naranja|"
           "amarillo|violeta|cafe|beige|crema|titanio|grafito|medianoche|estelar|marfil|mint|menta|celeste|turquesa|"
           "oscuro|claro|hielo|cielo|noche|obsidiana|onix|cobre|bronce|coral|purpura|magenta|negra|silver|black|"
           "white|blue|green|gold|pink|gray|grey|purple|lilac|red|cyan")
RUIDO = (r"celular|smartphone|telefono|movil|libre|nuevo|dual sim|dual|sim|5g|4g|lte|ram|"
         r"gb|tb|mp|mah|pulgadas|nfc|esim|con|de|y")

CONDICION_USADO = re.compile(r"reacondicionad|refurbish|renovad|usado|open box|segunda mano|seminuevo")
NO_CELULAR = re.compile(
    r"\b(funda|protector|cargador|cable|audifonos?|reloj|smartwatch|watch|tablet|tv|televisor|case|estuche|"
    r"vidrio|soporte|adaptador|parlante|barra|power ?bank|bateria|kit|lente|camara|gimbal|gafas|repuesto|pantalla "
    r"de repuesto|band|banda|manilla|tarjeta de memoria|memoria sd)\b")

# Patrón del modelo por marca (se busca sobre el nombre normalizado). El primer grupo con nombre 'm' es el modelo.
_MOD = {
    "Samsung": r"(?:galaxy\s+)?(?P<m>(?:z\s?(?:flip|fold)\s?\d+|s\s?\d{2}\s?(?:ultra|plus|\+|fe)?|"
               r"[amfe]\s?\d{2,3}[se]?(?:\s?(?:ultra|plus|\+|fe|lite))?|xcover\s?\d+|note\s?\d+))",
    "Apple": r"iphone\s*(?P<m>(?:se|x[rs]?|\d{1,2})(?:\s?(?:pro max|pro|plus|mini|e|air))?)",
    "Xiaomi": r"(?P<m>(?:redmi\s?note\s?\d+[a-z]?(?:\s?(?:pro\s?\+|pro\s?plus|pro|\+))?|"
              r"redmi\s?(?:turbo\s?)?\d*[a-z]?\d*[a-z]?|poco\s?[a-z]\d+[a-z]*(?:\s?(?:pro|gt))?|"
              r"xiaomi\s?\d+[a-z]*(?:\s?(?:ultra|pro|lite|t pro|t))?|mi\s?\d+[a-z]*))",
    "Motorola": r"(?P<m>(?:moto\s?)?(?:edge\s?\d+[a-z]*(?:\s?(?:plus|neo|fusion|ultra|pro|lite))?|"
                r"razr\s?\d*[a-z]*(?:\s?(?:plus|ultra))?|[gec]\s?\d{1,3}[a-z]*(?:\s?(?:power|plus|play|pro|ultra|fusion|neo|stylus))?))",
    "Honor": r"honor\s*(?P<m>(?:magic\s?v?\d*[a-z]*(?:\s?(?:pro|lite))?|x\s?\d+[a-z]*(?:\s?(?:plus|pro|lite))?|"
             r"\d{2,3}[a-z]*(?:\s?(?:pro|lite|smart))?|play\s?\d*[a-z]*))",
    "Infinix": r"(?P<m>(?:hot|note|smart|zero|gt)\s?\d+[a-z]*(?:\s?(?:pro|plus|\+|play|ultra|s|i))?)",
    "Tecno": r"(?P<m>(?:spark(?:\s?go)?|camon|pova|phantom\s?[xv]\d?)\s?\d*[a-z]*(?:\s?(?:pro|plus|neo|premier|pop))?)",
    "Oppo": r"(?P<m>(?:reno\s?\d+[a-z]*|a\s?\d{2,3}[a-z]*|find\s?[xn]\d*)(?:\s?(?:pro\s?\+|pro|plus|lite|neo|f))?)",
    "Realme": r"realme\s*(?P<m>(?:gt\s?\d*[a-z]*|note\s?\d+[a-z]*|narzo\s?\d+[a-z]*|[c]?\d{1,3}[a-z]*)(?:\s?(?:pro\s?\+|pro|plus|\+|lite|x))?)",
    "ZTE": r"(?P<m>(?:blade|nubia|axon)\s?[a-z]*\s?\d*[a-z]*(?:\s?(?:pro|plus|ultra|neo))?)",
}


def detectar_marca(nombre: str, marca_tienda: str = "") -> str | None:
    for fuente in (normalizar(marca_tienda), normalizar(nombre)):
        for token in fuente.split():
            if token in config.ALIAS_MARCA:
                return config.ALIAS_MARCA[token]
    return None


def detectar_almacenamiento(nombre: str) -> int | None:
    """GB de almacenamiento interno (los valores típicos de RAM se descartan)."""
    n = normalizar(nombre)
    valores = []
    for cant, unidad in re.findall(r"(\d+)\s*(gb|tb)", n):
        gb = int(cant) * (1024 if unidad == "tb" else 1)
        if gb in (32, 64, 128, 256, 512, 1024):
            valores.append(gb)
    return max(valores) if valores else None


def detectar_ram(nombre: str) -> int | None:
    n = normalizar(nombre)
    m = re.search(r"(\d+)\s*gb\s*ram|ram\s*(\d+)\s*gb|(\d+)\s*\+\s*\d+\s*gb", n)
    if m:
        return int(next(g for g in m.groups() if g))
    for cant in re.findall(r"(\d+)\s*gb", n):
        if int(cant) in (2, 3, 4, 6, 8, 12, 16):
            return int(cant)
    return None


def detectar_condicion(nombre: str) -> str:
    return "reacondicionado" if CONDICION_USADO.search(normalizar(nombre)) else "nuevo"


def es_celular(nombre: str) -> bool:
    return not NO_CELULAR.search(normalizar(nombre))


def detectar_modelo(nombre: str, marca: str | None) -> str | None:
    """Devuelve el modelo normalizado (ej. 'a55', 'redmi note 13 pro', 'iphone 15 pro max') o None."""
    if not marca:
        return None
    n = normalizar(nombre)
    patron = _MOD.get(marca)
    if patron:
        m = re.search(patron, n)
        if m:
            modelo = re.sub(r"\s+", " ", m.group("m")).strip()
            modelo = re.sub(r"\b([a-z])\s(\d)", r"\1\2", modelo)      # 'a 55' -> 'a55'
            modelo = re.sub(r"(\d)(ultra|plus|fe|pro|lite|fusion|neo)\b", r"\1 \2", modelo)   # 's26ultra' -> 's26 ultra'
            modelo = modelo.replace("pro plus", "pro+").replace(" +", "+").replace(" plus", "+")
            if marca == "Motorola":
                modelo = re.sub(r"^moto\s*", "", modelo)   # 'moto g24' y 'g24' son el mismo modelo
            return f"iphone {modelo}" if marca == "Apple" else modelo
    return None


# ------------------------------------------------------------------ Televisores
NO_TELEVISOR = re.compile(
    r"^(soporte|control|antena|cable|base|mueble|protector|proyector|monitor|decodificador|barra|parlante|"
    r"tv box|convertidor|adaptador|limpiador|kit|rack|forro)\b|\bpara (tv|televisor)")
ES_TV = re.compile(r"\b(tv|televisor|television|pulgadas)\b")
COMBO_TV = re.compile(r"\b(combo|barra|incluye|marco|obsequio|regalo)\b")
# Código de modelo: [prefijo] + pulgadas + serie + número + letra de año. Ej. 'UN65U8000HKXZL' -> '65u8000h'
_MOD_TV = re.compile(r"(?<![a-z0-9])(?:un|qn|kd|xr|oled|qled|l)?\s?(?P<p>\d{2,3})(?P<s>[a-z]{1,3})(?P<n>\d{1,4})(?P<a>[a-z]?)")
_PULGADAS = re.compile(r"(\d{2,3})(?:[.,]\d)?\s*(?:\"|″|”|“|′|'|pulgadas|pulg|pul\b|in\b|inch)", re.I)


def es_televisor(nombre: str) -> bool:
    n = normalizar(nombre)
    return bool(ES_TV.search(n)) and not NO_TELEVISOR.search(n)


def es_combo(nombre: str) -> bool:
    """TV que se vende con otro artículo (barra de sonido, marco): no es comparable con el TV solo."""
    return bool(COMBO_TV.search(normalizar(nombre)))


def detectar_modelo_tv(nombre: str, pulgadas: int | None = None) -> str | None:
    """Código de modelo sin prefijo de línea ni sufijo regional. Si se conocen las pulgadas, exige que coincidan."""
    for m in _MOD_TV.finditer(normalizar(nombre)):
        tam = int(m.group("p"))
        if not 19 <= tam <= 120 or (pulgadas and tam != pulgadas):
            continue
        return f"{tam}{m.group('s')}{m.group('n')}{m.group('a')}"
    return None


def detectar_pulgadas(nombre: str) -> int | None:
    """Tamaño de pantalla desde el texto ('65\"', '65 pulgadas'); si no aparece, desde el código de modelo."""
    for cant in _PULGADAS.findall(str(nombre)):
        if 19 <= int(cant) <= 120:
            return int(cant)
    modelo = detectar_modelo_tv(nombre)
    return int(re.match(r"\d+", modelo).group()) if modelo else None
