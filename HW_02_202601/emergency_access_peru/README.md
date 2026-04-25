# Emergency Healthcare Access Inequality in Peru

## What this project does
This repository builds a district-level emergency healthcare access analysis for Peru by integrating:

- health facility information (IPRESS),
- emergency activity records (SUSALUD C1),
- populated centers geospatial data,
- district boundaries.

The project includes a reproducible processing pipeline in `src/` and a Streamlit application in `app.py` with exactly 4 tabs.

## Main analytical goal
Estimate and compare emergency healthcare access conditions across districts, identify relatively underserved territories, and evaluate how sensitive conclusions are to the definition of an emergency-access facility.

## Datasets used
- `data/raw/IPRESS_Health_Facilities/IPRESS.csv`
- `data/raw/Consulta_C1_IPRESS/ConsultaC1_2026_v4.csv`
- `data/raw/Populated_Centers/CCPP_IGN100K.shp`
- `data/raw/District_Boundaries_of_Peru/DISTRITOS.shp`

## Repository structure
```text
emergency_access_peru/
|-- app.py
|-- README.md
|-- requirements.txt
|-- src/
|-- data/
|   |-- raw/
|   `-- processed/
|-- output/
|   |-- figures/
|   `-- tables/
`-- video/
    `-- link.txt
```

## Data cleaning and preprocessing
Main cleaning decisions implemented in `src/cleaning.py` and supporting modules:

- standardize key text and code fields (`ubigeo`, `codigo_unico`, `co_ipress`, location names),
- preserve missing and zero emergency activity values for traceability,
- create score-ready filled numeric fields (`*_for_score`) while keeping raw quality flags,
- treat non-numeric or suppressed C1 values as unavailable for scoring only after preserving flags,
- fix IPRESS coordinate interpretation (`NORTE` as longitude, `ESTE` as latitude),
- create GeoDataFrames and assign points to districts using spatial joins,
- compute straight-line distances in EPSG:32718, a projected metric CRS.

Distances should be interpreted as proximity proxies, not travel times. Peru spans UTM zones 17S, 18S, and 19S, so EPSG:32718 is an approximation for national analysis.

## District-level metrics and framework
Implemented in `src/metrics.py`.

### Q1 Territorial Availability
- Facility component: all facilities plus structural emergency-proxy facilities.
- Emergency proxy categories: `I-4`, `II-1`, `II-2`, `II-E`, `III-1`, `III-2`, `III-E`.
- Activity component: C1 emergency attentions and attended counts.
- Scaling: `log1p` plus min-max scaling.
- Final score: `Q1 = 0.50 * facility_component + 0.50 * activity_component`.

### Q2 Settlement Access
For each populated center, the pipeline computes the straight-line distance to the nearest structural emergency-proxy facility. District aggregation includes:

- `median_distance_km`,
- `p90_distance_km`,
- `share_over_20km`,
- `share_over_30km`,
- `matched_centers`,
- `total_populated_centers`.

Final score:

```text
distance_component = 1 - minmax(log1p(median_distance_km))
remote_tail_component = 1 - share_over_30km
Q2 = 0.70 * distance_component + 0.30 * remote_tail_component
```

`coverage_share` is kept as a diagnostic but is not part of the Q2 score.

### Q3 Combined District Comparison
Baseline score:

```text
Q3 = 0.50 * Q1 + 0.50 * Q2_structural
```

`Q2_structural` uses the structural emergency-proxy facility set from IPRESS categories.

### Q4 Methodological Sensitivity
Alternative score:

```text
Q4 = 0.50 * Q1 + 0.50 * Q2_observed
```

`Q2_observed` recomputes nearest-facility access using a different facility set: IPRESS with observed positive C1 emergency activity. Q4 therefore tests sensitivity to the emergency-facility definition, not just sensitivity to score weights.

Rank shifts compare Q3 baseline vs Q4 alternative. These shifts are sensitivity diagnostics, not proof that a district improved or worsened in reality.

## Literature framing
This project uses a multidimensional access framing: availability/activity, geographic accessibility, and realized use.

- Penchansky and Thomas (1981) motivate treating access as multidimensional.
- Luo and Wang (2003) motivate considering service supply and spatial separation in GIS-based access analysis.
- McGrail (2012) motivates reporting distance thresholds and spatial isolation tails rather than simple counts only.
- WHO emergency care system guidance motivates treating emergency care as a system, while this project uses IPRESS category as an operational structural proxy.

This project does not implement a full 2-Step Floating Catchment Area method. It uses nearest-facility straight-line distance as a simplified proximity proxy because population demand by populated center, facility supply capacity, and catchment-level ratios are outside the scope of this homework.

## Static and interactive outputs
Static outputs are saved in `output/figures/` and district tables in `output/tables/`.

Interactive exploration is available in Streamlit Tab 4 using Folium district maps for:

- Q3 baseline combined score,
- Q4 alternative combined score,
- Q4 rank shift,
- Q1 territorial availability,
- Q2 settlement access.

## Installation
Use the `ds_2026` environment.

```powershell
conda activate ds_2026
pip install -r requirements.txt
```

## How to run the processing pipeline
Run all analytical stages:

```powershell
python -m src.question1_pipeline
python -m src.question2_pipeline
python -m src.question3_4_pipeline
```

## How to run the Streamlit app
```powershell
streamlit run app.py
```

## Streamlit pipeline buttons
In the sidebar:

- `Run Q1 pipeline`: rebuilds Q1 tables and figures.
- `Run Q2 pipeline`: rebuilds Q2 geospatial access tables and figures.
- `Run Q3 + Q4 pipeline`: rebuilds combined baseline/alternative comparison and sensitivity outputs.

After each run, the app clears cache for that block and refreshes visuals/tables.

## Main limitations
- IPRESS category is a structural proxy, not direct verification of emergency capacity.
- C1 positive activity is evidence of observed emergency use, not a complete ground truth.
- Missing or suppressed C1 values may reflect reporting or privacy rules, not absence of care.
- Populated centers are treated equally because population counts by center are not integrated.
- Straight-line distances do not model travel time, roads, rivers, terrain, or referral pathways.
- District-level aggregation can hide within-district inequality.
- Facilities without valid coordinates cannot be used for nearest-distance calculations.

## Reproducibility notes
- Keep raw files under the expected `data/raw/` subfolders.
- Run pipelines before opening the app if outputs do not exist yet.
- If raw data changes, re-run all three pipelines in sequence.
