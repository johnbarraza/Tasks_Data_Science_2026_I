# Avance HW3

## 2026-05-14

- Leidas instrucciones completas de HW3.
- Confirmado que se debe ignorar `HW_01_202601` y `HW_02_202601`.
- Creada rama de trabajo `feature/hw3-raster-rag` desde `main` actualizado.
- Detectados datos locales para los dos tasks.
- Normalizadas carpetas `notebook/` a `notebooks/`.
- Creados README, requirements, gitignore, notebooks, archivos de video y handoff.
- Ejecutado Task 1 completo en `conda` env `ds_2026`.
- Generados outputs de Task 1:
  - `output/vnl_norm.tif`
  - `output/conn_norm.tif`
  - `output/ibd_brecha_digital.tif`
  - `output/clasificacion_brecha.tif`
  - `output/dashboard_brecha_digital.png`
- Verificado Task 2 primero en modo offline sin `.env`: extraccion PDF, tokenizacion, chunking, ChromaDB vacio y UI placeholder ejecutaron sin error.
- Confirmado que los requirements de RAG estan instalados en `ds_2026`.
- Ejecutado Task 2 con `.env` local y `GEMINI_API_KEY`.
- Indexada coleccion ChromaDB local `chroma_db_beca18` con 491 chunks.
- Notebook RAG reejecutado con outputs visibles.

## Pendiente

- Grabar video y reemplazar `PENDIENTE` en ambos `video/link.txt`.
- Crear PR desde `feature/hw3-raster-rag` hacia `main`.
