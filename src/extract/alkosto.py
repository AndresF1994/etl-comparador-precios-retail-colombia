import re
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from .base import ExtractorTienda, a_precio


class _Hybris(ExtractorTienda):
    """Alkosto y Alkomprar comparten plataforma (Hybris + Algolia) y el mismo HTML de tarjetas."""
    dominio = ""
    selector_tarjeta = "li.product__item"

    def url_busqueda(self, termino):
        return f"https://www.{self.dominio}/search?text={quote_plus(termino)}"

    def parsear(self, html, busqueda):
        soup = BeautifulSoup(html, "html.parser")
        ofertas = []
        for c in soup.select("li.product__item"):
            titulo = c.select_one("h3.product__item__top__title")
            enlace = c.select_one("a.product__item__top__link")
            precio = c.select_one("span.price")
            if not (titulo and enlace and precio):
                continue
            href = enlace["href"].split("?")[0]
            m = re.search(r"/p/(\d+)", href)
            viejo = c.select_one("p.product__price--discounts__old")
            actual = a_precio(precio.get_text())
            ofertas.append({
                "tienda": self.tienda, "busqueda": busqueda,
                "nombre": titulo.get_text(strip=True), "marca_tienda": "",
                "url": f"https://www.{self.dominio}{href}",
                "ean": m.group(1) if m else None,
                "precio_actual": actual,
                "precio_original": a_precio(viejo.get_text()) if viejo else actual,
                "vendedor": self.tienda,
            })
        return ofertas


class Alkosto(_Hybris):
    tienda = "Alkosto"
    dominio = "alkosto.com"


class Alkomprar(_Hybris):
    tienda = "Alkomprar"
    dominio = "alkomprar.com"
