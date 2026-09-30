"""Genera el PDF de la Entrega 2: python -m src.informe
Copia las figuras del EDA junto al HTML del informe y lo imprime a PDF con el Chromium de Playwright."""
import shutil
from playwright.sync_api import sync_playwright
from src import config

DIR_INFORME = config.RAIZ / "docs" / "entrega_2"
HTML = DIR_INFORME / "entrega_etapa_2.html"
PDF = DIR_INFORME / "entrega_etapa_2.pdf"


def main():
    destino_fig = DIR_INFORME / "figuras"
    destino_fig.mkdir(parents=True, exist_ok=True)
    for png in (config.DIR_REPORTES / "eda").glob("fig*.png"):
        shutil.copy2(png, destino_fig / png.name)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(HTML.as_uri(), wait_until="networkidle")
        page.pdf(path=str(PDF), format="Letter", print_background=True,
                 margin={"top": "14mm", "bottom": "14mm", "left": "16mm", "right": "16mm"},
                 display_header_footer=True, header_template="<span></span>",
                 footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#888">'
                                 '<span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        browser.close()
    print(f"PDF generado: {PDF}")


if __name__ == "__main__":
    main()
