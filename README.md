# Comparador de precios: Éxito, Falabella, Alkosto y Alkomprar

Pipeline ETL académico (Maestría en IA y Ciencia de Datos, asignatura ETL) que extrae, homologa y compara precios
de **celulares y televisores** entre cuatro tiendas colombianas, y construye un histórico diario de precios.

## Flujo ETL
| Etapa | Módulo | Qué hace |
|---|---|---|
| **E** | `src/extract/` | Búsqueda por categoría y marca en cada tienda con Playwright; el parseo (BeautifulSoup / JSON `__NEXT_DATA__`) es una función pura probada con HTML guardados. Crudo en `data/raw/ofertas_raw_AAAA-MM-DD.csv`. |
| **T** | `src/transform/` | Limpieza, deduplicación, filtro de accesorios, rango de precio por categoría, extracción de atributos (marca, modelo, almacenamiento / pulgadas, combo, condición, tipo de vendedor), marca de descuentos sospechosos, colapso de colores y clave común `producto_id`. |
| **L** | `src/load/db.py` | SQLite `data/precios.db`, tabla `ofertas` con una fila por producto + tienda + vendedor + fecha (idempotente por fecha). |
| Análisis | `src/eda.py`, `src/analisis.py` | EDA y calidad de datos (figuras + `metricas.json`); comparativa para el comprador (Excel + gráficos). |

Clave de homologación (`producto_id`):
- Celulares: `celular | marca | modelo | almacenamiento` (ej. `celular | samsung | a56 | 256gb`).
- Televisores: `televisor | marca | código de modelo | pulgadas [+combo]` (ej. `televisor | samsung | 65u8000h | 65in`).
  El código se normaliza quitando prefijo de línea y sufijo regional: `UN65U8000HKXZL` y `65U8000H` → `65u8000h`.

## Uso
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

python -m src.pipeline                                     # extracción completa del día (≈30 min)
python -m src.pipeline --categorias televisor --marcas LG  # parcial
python -m src.pipeline --solo-transformar --fecha 2026-09-28   # reprocesa un crudo sin navegar
python -m src.eda                                          # EDA y calidad -> data/reportes/eda/
python -m src.analisis --categoria televisor               # comparativa -> data/reportes/
python -m src.informe                                      # PDF de la Entrega 2 (docs/)
pytest -q
```

## Programar la corrida diaria (histórico)
`run_diario.bat` ejecuta el pipeline y deja log en `data/logs/`. Para programarlo en Windows a las 7:00 a.m.:
```
schtasks /create /tn "ComparadorPrecios" /tr "\"%CD%\run_diario.bat\"" /sc daily /st 07:00
```

## Buenas prácticas de extracción
- Solo datos públicos del listado de búsqueda, una página por búsqueda, pausas de `PAUSA_SEG` entre peticiones
  y sin paralelismo. Uso exclusivamente académico.
- Revisar `robots.txt` y términos de uso de cada sitio antes de ampliar la frecuencia o el alcance.

## Entregables
- `docs/entrega_2/`: informe de la Entrega 2 (EDA, calidad de datos por V's, transformaciones y trazabilidad).
