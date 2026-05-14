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

## Main interpretation

Bright zones in the nighttime lights layer indicate the main urban and economically active areas. Areas with high VNL but low connectivity are priority zones for digital inclusion, while areas with both low VNL and low connectivity reveal broader territorial exclusion.
