# Task 1 - Web Scraping UNMSM (Python + Selenium)

Este proyecto extrae automaticamente los resultados del examen de admision de la UNMSM por cada carrera y consolida todo en un solo archivo Excel.

## Estructura

- `scraper.py`: script principal.
- `output/resultados_sanmarcos.xlsx`: salida consolidada.
- `video/link.txt`: link del video explicativo.

## Requisitos

- Python 3.10+
- Google Chrome instalado
- Entorno conda `ds_2026`

## Instalacion

```powershell
conda activate ds_2026
pip install selenium pandas openpyxl beautifulsoup4 webdriver-manager
```

## Ejecucion

```powershell
conda activate ds_2026
cd C:\Users\johnb\Documents\Github\Tasks_Data_Science_2026_I\HW_01_202601\Scraping_data
python scraper.py
```

Si quieres ver el navegador mientras corre:

```powershell
python scraper.py --show-browser
```

## Como se resuelve el problema de los 50 registros

La tabla usa DataTables y por defecto solo muestra 50 filas por pagina. El script:

1. Intenta cambiar el selector de cantidad de filas para mostrar todas.
2. Si no se puede mostrar todo de una vez, navega pagina por pagina con `Next`.
3. Deduplica filas para evitar registros repetidos.

Asi se extraen **todos los postulantes** y no solo los primeros 50.

## Salida

Se genera:

- `output/resultados_sanmarcos.xlsx`

Columnas principales:

- `carrera`
- `source_url`
- columnas originales de la tabla de cada carrera.
