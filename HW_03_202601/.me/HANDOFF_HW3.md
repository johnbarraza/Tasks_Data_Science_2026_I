# HW3 handoff

## Estado actual

Se esta trabajando en la rama `feature/hw3-raster-rag`.

La estructura esperada para ambos proyectos fue normalizada con carpetas `notebooks/` y `video/`. Los archivos de planeamiento y continuidad viven en `HW_03_202601/.me`.

## Como continuar

1. Instalar dependencias de cada proyecto:

```powershell
python -m pip install -r HW_03_202601\raster-digital-divide\requirements.txt
python -m pip install -r HW_03_202601\beca18-rag-chatbot\requirements.txt
```

2. Para Task 2, crear `.env` local desde `.env.example`:

```text
GEMINI_API_KEY=tu_api_key
```

3. Ejecutar los notebooks completos:

```powershell
jupyter nbconvert --to notebook --execute --inplace HW_03_202601\raster-digital-divide\notebooks\digital_divide_cusco.ipynb
jupyter nbconvert --to notebook --execute --inplace HW_03_202601\beca18-rag-chatbot\notebooks\beca18_rag_chatbot.ipynb
```

4. Revisar outputs:

- Task 1 debe generar `output/vnl_norm.tif`, `output/conn_norm.tif`, `output/ibd_brecha_digital.tif`, `output/clasificacion_brecha.tif` y `output/dashboard_brecha_digital.png`.
- Task 2 debe poblar `chroma_db_beca18/` localmente y mostrar respuestas con fuentes.

5. Grabar video de maximo 5 minutos, subirlo y reemplazar `PENDIENTE` en:

- `raster-digital-divide/video/link.txt`
- `beca18-rag-chatbot/video/link.txt`

## Notas de seguridad

- No commitear `.env`.
- No commitear `chroma_db_*`.
- No commitear rasters crudos ni zips de Task 1.
- No tocar cambios pendientes de `HW_02_202601`.
