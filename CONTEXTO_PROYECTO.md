# Contexto del proyecto (para retomar en otra sesión)

## Objetivo
Proyecto **académico** (Maestría IA y Ciencia de Datos, asignatura ETL): pipeline ETL que extrae, homologa y compara
precios de **celulares y televisores** entre **Éxito, Falabella, Alkosto y Alkomprar**, y acumula un histórico diario.
La Entrega 1 (contexto, problema y fuentes) está en `../entrega_etapa_1.pdf`.

## Origen
Se inspira en un proyecto laboral de "Chequeo de precios" (repo privado). **No se copió código ni credenciales**:
solo la idea y algunos selectores públicos. Sin Bright Data ni servicios pagos.

## Estado (2026-09-29)
- Extractores funcionando en las 4 tiendas (búsqueda por categoría + marca, primera página de resultados).
- Crudos: `data/raw/ofertas_raw_2026-09-28.csv` (solo celulares) y `..._2026-09-29.csv` (celulares + televisores).
- Transformación por categoría con clave `producto_id` (ver README). Tests: `pytest -q`.
- Entrega 2 (EDA, V's, transformaciones, trazabilidad): `docs/entrega_2/informe_entrega_2.pdf`,
  generado con `python -m src.eda` + `python -m src.informe`. Los números del texto salen de
  `data/reportes/eda/metricas.json`; si se re-ejecuta el EDA con más fechas hay que actualizar el HTML.

## Pendientes (Entrega 3 en adelante)
1. Programar `run_diario.bat` para acumular ≥ 6 semanas (volumen previsto en la Entrega 1).
2. Indicadores para el consumidor: precio vs. mínimo histórico, "¿es buena oferta hoy?", alertas de ahorro.
3. Mejorar la homologación de Falabella/Éxito cuando el título no trae el código de modelo (leer la ficha).
4. Confirmar `robots.txt` y términos de uso de cada sitio; mantener las pausas.
