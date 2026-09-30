import json
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from .base import ExtractorTienda, a_precio


class Falabella(ExtractorTienda):
    """Falabella es Next.js: los resultados (48 por página) vienen en el JSON de __NEXT_DATA__."""
    tienda = "Falabella"

    def url_busqueda(self, termino):
        return f"https://www.falabella.com.co/falabella-co/search?Ntt={quote_plus(termino)}"

    def parsear(self, html, busqueda):
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag:
            return []
        resultados = json.loads(tag.string)["props"]["pageProps"].get("results", [])
        ofertas = []
        for p in resultados:
            # crossed=True es el precio tachado; cmrPrice es precio con tarjeta y se excluye para comparar parejo
            precios = {x["type"]: a_precio((x.get("price") or [None])[0]) for x in p.get("prices", [])}
            actual = precios.get("eventPrice") or precios.get("internetPrice")
            original = precios.get("normalPrice") or actual
            if not actual:
                continue
            ofertas.append({
                "tienda": self.tienda, "busqueda": busqueda,
                "nombre": p.get("displayName", ""), "marca_tienda": p.get("brand", ""),
                "url": p.get("url", ""), "ean": None,
                "precio_actual": actual, "precio_original": original,
                "vendedor": p.get("sellerName") or "Falabella",
            })
        return ofertas
