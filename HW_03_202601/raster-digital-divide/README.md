# Raster Digital Divide

This project analyzes the territorial digital divide in Cusco, Peru, by combining nighttime lights and mobile coverage raster data.

## Research question

Where does Cusco show evidence of active digital divide, meaning populated or economically active zones with low mobile connectivity, and where does it show broader social exclusion risk?

## Data

Place the required input files in `data/` before running the notebook:

- `VNL_cusco_2025.tif`: NASA Black Marble nighttime radiance, CRS EPSG:4326.
- `kernel_cobmovil2019_50m.tif`: OSIPTEL mobile coverage kernel density, CRS EPSG:32719.

The raw raster files are intentionally excluded from git.

## Installation

```powershell
python -m pip install -r requirements.txt
```

## Run

Open and run all cells in:

```text
notebooks/digital_divide_cusco.ipynb
```

The notebook prints raster metadata, aligns the connectivity raster to the VNL grid, normalizes both layers, computes indices, produces maps, and exports GeoTIFF/PNG deliverables.

## Outputs

- `output/vnl_norm.tif`: normalized nighttime lights.
- `output/conn_norm.tif`: normalized connectivity raster aligned to the VNL grid.
- `output/ibd_brecha_digital.tif`: Digital Divide Index, `VNL_norm - Connectivity_norm`.
- `output/clasificacion_brecha.tif`: four-class territorial classification.
- `output/dashboard_brecha_digital.png`: final composite dashboard figure.

## Main findings

The territorial classification reveals that 96.97% of Cusco (≈209,530 km²) falls into the Critical Divide category — no meaningful nighttime light and no mobile connectivity. Urban Connected zones cover only 0.20% of the territory (≈436 km²), concentrated in the city of Cusco and secondary urban centers. The Pearson correlation between VNL and connectivity is r = 0.46 (p < 0.001), confirming that connectivity follows urbanization but with incomplete coverage even in lit areas. A Welch t-test comparing Urban Connected vs Critical Divide VNL values yields t = 11.06, p = 2.90e-15, Cohen d = 2.15, confirming the divide is statistically extreme.
