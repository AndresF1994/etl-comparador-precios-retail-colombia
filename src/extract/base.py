"""Capa de extracción (E): cada tienda separa la navegación (Playwright) del parseo (funciones puras).

El parseo recibe HTML y devuelve una lista de ofertas crudas, por lo que se puede probar sin red
con los HTML guardados en tests/fixtures.
"""
import re
from abc import ABC, abstractmethod

CAMPOS_OFERTA = ["tienda", "categoria", "busqueda", "nombre", "marca_tienda", "url", "ean",
                 "precio_original", "precio_actual", "vendedor"]


def a_precio(texto) -> int | None:
    """'$ 1.299.900' -> 1299900. Devuelve None si no hay dígitos."""
    limpio = re.sub(r"[^\d]", "", str(texto or ""))
    return int(limpio) if limpio else None


def scroll_hasta_estable(page, selector: str, max_rondas: int = 12, espera_ms: int = 1200) -> int:
    """Baja la página como lo haría un usuario hasta que deje de cargar tarjetas nuevas."""
    previo = -1
    for _ in range(max_rondas):
        actual = page.locator(selector).count()
        if actual == previo:
            break
        previo = actual
        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(espera_ms)
    return previo


class ExtractorTienda(ABC):
    tienda = ""

    @abstractmethod
    def url_busqueda(self, termino: str) -> str: ...

    @abstractmethod
    def parsear(self, html: str, busqueda: str) -> list[dict]:
        """HTML de resultados -> lista de dicts con CAMPOS_OFERTA."""

    selector_tarjeta = ""  # si se define, se hace scroll hasta que deje de cargar

    def extraer(self, page, termino: str, marca: str) -> list[dict]:
        page.goto(self.url_busqueda(termino), wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        if self.selector_tarjeta:
            scroll_hasta_estable(page, self.selector_tarjeta)
        return self.parsear(page.content(), marca)
