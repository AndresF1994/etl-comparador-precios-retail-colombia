from pathlib import Path
import pytest
from src.extract.alkosto import Alkosto, Alkomprar
from src.extract.exito import Exito
from src.extract.falabella import Falabella

FIX = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("extractor,archivo", [
    (Alkosto(), "alkosto.html"), (Alkomprar(), "alkomprar.html"),
    (Exito(), "exito.html"), (Falabella(), "falabella.html"),
])
def test_parseo_devuelve_ofertas_validas(extractor, archivo):
    html = (FIX / archivo).read_text(encoding="utf-8")
    ofertas = extractor.parsear(html, "Samsung")
    assert len(ofertas) >= 5
    for o in ofertas:
        assert o["nombre"] and o["url"].startswith("http")
        assert o["precio_actual"] and o["precio_actual"] > 50_000
        assert o["precio_original"] >= o["precio_actual"]
