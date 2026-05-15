# Contexto actual HW3

Actualizado: 2026-05-14
Branch: `feature/hw3-raster-rag`
Entorno usado: `conda` env `ds_2026`

## Resumen ejecutivo

HW3 esta implementado en dos proyectos separados dentro de `HW_03_202601`:

- `raster-digital-divide`: analisis geoespacial raster de brecha digital en Cusco.
- `beca18-rag-chatbot`: pipeline RAG sobre el reglamento oficial de Beca 18.

Ambos notebooks existen, fueron ejecutados y quedaron con outputs visibles. Task 1 genero los archivos raster/PNG pedidos. Task 2 indexo localmente el PDF en ChromaDB y ejecuto el flujo RAG con Gemini usando `.env` local.

## Que se hizo

### Preparacion general

- Se creo la rama `feature/hw3-raster-rag` desde `main` actualizado.
- Se ignoro cualquier trabajo de `HW_01_202601` y `HW_02_202601`.
- Se normalizaron carpetas `notebook/` a `notebooks/`.
- Se agregaron `README.md`, `requirements.txt`, `.gitignore`, `video/link.txt` y documentacion de continuidad.
- Se creo `HW_03_202601/.me/build_hw3_notebooks.py` para regenerar los notebooks desde una fuente reproducible.

### Task 1: raster-digital-divide

- Notebook creado: `raster-digital-divide/notebooks/digital_divide_cusco.ipynb`.
- Ejecutado completo en `ds_2026`.
- Implementa:
  - inspeccion de rasters;
  - reproyeccion y alineamiento al grid VNL;
  - normalizacion percentil 2-98;
  - mapas VNL, IBD/EDT, prioridad de intervencion y riesgo de exclusion;
  - clasificacion territorial 2x2;
  - resumen estadistico, correlacion, KDE y Welch t-test;
  - exportacion de entregables.
- Outputs generados:
  - `raster-digital-divide/output/vnl_norm.tif`
  - `raster-digital-divide/output/conn_norm.tif`
  - `raster-digital-divide/output/ibd_brecha_digital.tif`
  - `raster-digital-divide/output/clasificacion_brecha.tif`
  - `raster-digital-divide/output/dashboard_brecha_digital.png`

### Task 2: beca18-rag-chatbot

- Notebook creado: `beca18-rag-chatbot/notebooks/beca18_rag_chatbot.ipynb`.
- PDF normalizado a `data/beca18_reglamento.pdf`.
- Ejecutado primero sin `.env` para validar la ruta offline.
- Ejecutado despues con `.env` local y `GEMINI_API_KEY`.
- ChromaDB local `chroma_db_beca18/` fue poblado con 491 chunks.
- Implementa:
  - extraccion por pagina con `[PAGE N]`;
  - limpieza ligera;
  - conteo de tokens con `tiktoken`;
  - chunking con `RecursiveCharacterTextSplitter`;
  - embeddings `gemini-embedding-001` con task types separados;
  - persistencia ChromaDB con distancia coseno;
  - busqueda semantica;
  - respuesta grounded con `gemini-2.5-flash`;
  - interfaz `ipywidgets` con fuentes expandibles.

## Decisiones clave

- Usar una sola rama para todo HW3: `feature/hw3-raster-rag`.
- Mantener ambos proyectos dentro de `HW_03_202601`, aunque la consigna hable de repositorios separados, porque el workspace del curso esta organizado por homework.
- No commitear datos pesados ni secretos:
  - rasters crudos en `raster-digital-divide/data/`;
  - `.env`;
  - `chroma_db_*`;
  - zips o auxiliares locales.
- Si el notebook RAG se ejecuta sin API key, no debe fallar; debe correr la parte offline y saltar embeddings/generacion.
- Se conserva `build_hw3_notebooks.py` en `.me` como fuente reproducible para regenerar notebooks si se editan accidentalmente.
- Se commitearon outputs procesados de Task 1 porque son entregables finales pequenos y pedidos por la consigna.
- Se commiteo `beca18_reglamento.pdf` porque es el documento fuente requerido para que el notebook RAG corra end-to-end; los PDFs duplicados con nombre original se ignoran.

## Supuestos

- `ds_2026` es el entorno oficial de trabajo para ejecutar ambos notebooks.
- La API key de Gemini existe solo en `.env` local y no debe subirse.
- `chroma_db_beca18/` puede regenerarse desde el notebook, por eso permanece fuera de git.
- Los rasters originales ya estan disponibles localmente en `raster-digital-divide/data/`.
- El video aun no esta grabado; por eso `video/link.txt` mantiene `PENDIENTE` en ambos proyectos.
- Los cambios untracked de `.claude/` y `HW_02_202601` no pertenecen a HW3 y deben ignorarse.

## Estado de git

Commits relevantes recientes:

- `8ffb182 feat(rag): record executed chatbot notebook`
- `24a05ac chore(hw3): document execution status and offline RAG path`
- `b2626ff feat(raster): export executed analysis deliverables`
- `17e2ead fix(hw3): make generated notebooks executable`
- `57167e7 feat(rag): add Beca 18 retrieval chatbot notebook`
- `5dfeea0 feat(raster): add digital divide analysis notebook`
- `1ece4d2 chore(rag): add normalized source document`
- `db48094 chore(hw3): scaffold assignment projects`

## Pendiente

- Grabar video de maximo 5 minutos.
- Subir video a YouTube no listado o Google Drive.
- Reemplazar `PENDIENTE` en:
  - `raster-digital-divide/video/link.txt`
  - `beca18-rag-chatbot/video/link.txt`
- Crear PR desde `feature/hw3-raster-rag` hacia `main`.
