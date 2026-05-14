# HW3 plan

Fecha: 2026-05-14
Branch de trabajo: `feature/hw3-raster-rag`

## Alcance

HW3 tiene dos proyectos independientes y un video comun:

1. `raster-digital-divide`: analisis raster de brecha digital territorial en Cusco.
2. `beca18-rag-chatbot`: chatbot RAG sobre el reglamento oficial de Beca 18.
3. `video/link.txt` en ambos proyectos con el enlace final del video.

Se ignoran `HW_01_202601` y `HW_02_202601` para esta entrega.

## Plan de trabajo

1. Normalizar estructura de carpetas exigida por la consigna.
2. Crear notebooks principales:
   - `raster-digital-divide/notebooks/digital_divide_cusco.ipynb`
   - `beca18-rag-chatbot/notebooks/beca18_rag_chatbot.ipynb`
3. Crear archivos de soporte:
   - `README.md`
   - `requirements.txt`
   - `.gitignore`
   - `.env.example` para el RAG
   - `video/link.txt`
4. Evitar commitear:
   - rasters crudos o zips en Task 1
   - `.env`
   - `chroma_db_*`
   - API keys
5. Hacer commits progresivos con mensajes descriptivos.

## Datos locales detectados

Task 1:

- `raster-digital-divide/data/VNL_cusco_2025.tif`
- `raster-digital-divide/data/kernel_cobmovil2019_50m.tif`
- archivos auxiliares PNG y ZIP locales, no necesarios para git.

Task 2:

- `beca18-rag-chatbot/data/7778068-rde-n-033-2026-minedu-vmgi-pronabec.pdf`
- `beca18-rag-chatbot/data/7778068-rde-n-033-2026-minedu-vmgi-pronabec-fe-de-erratas.pdf`
- copia normalizada creada: `beca18-rag-chatbot/data/beca18_reglamento.pdf`

## Riesgos

- El entorno local no tenia instalados `rasterio` ni `tiktoken` al iniciar.
- Task 2 necesita `GEMINI_API_KEY` en `.env`; no se debe hardcodear.
- Los notebooks deben ejecutarse antes de entrega final para que las salidas queden visibles.
