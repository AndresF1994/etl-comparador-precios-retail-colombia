import re
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base import ExtractorTienda, a_precio


class Exito(ExtractorTienda):
    """Éxito (VTEX/FastStore): tarjetas renderizadas; las de marketplace llevan '-mp' en la URL."""
    tienda = "Exito"
    selector_tarjeta = "article[class*=productCard_productCard]"

    def url_busqueda(self, termino):
        return f"https://www.exito.com/s?q={quote(termino)}"

    def parsear(self, html, busqueda):
        soup = BeautifulSoup(html, "html.parser")
        ofertas = []
        for c in soup.select("article[class*=productCard_productCard]"):
            enlace = c.select_one("a[data-testid=product-link]")
            nombre = c.select_one("h3[class*=styles_name]")
            marca = c.select_one("h3[class*=styles_brand]")
            actual_tag = c.select_one("[class*=ProductPrice_container]")
            if not (enlace and nombre and actual_tag):
                continue
            tachado = c.select_one("[class*=price-dashed]")
            actual = a_precio(actual_tag.get_text())
            href = enlace["href"]
            ofertas.append({
                "tienda": self.tienda, "busqueda": busqueda,
                "nombre": nombre.get_text(strip=True),
                "marca_tienda": marca.get_text(strip=True) if marca else "",
                "url": f"https://www.exito.com{href}", "ean": None,
                "precio_actual": actual,
                "precio_original": a_precio(tachado.get_text()) if tachado else actual,
                "vendedor": "Marketplace" if re.search(r"-mp/p$", href) else "Exito",
            })
        return ofertas
