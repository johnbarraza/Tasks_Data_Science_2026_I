# Emergency Healthcare Access Inequality in Peru

## What this project does
This repository builds a full district-level emergency healthcare access analysis for Peru by integrating:
- health facility information (IPRESS),
- emergency activity records (SUSALUD C1),
- populated centers geospatial data,
- district boundaries.

The project includes a reproducible processing pipeline (`src/`) and a Streamlit application (`app.py`) with exactly 4 tabs.

## Main analytical goal
Estimate and compare emergency healthcare access conditions across districts, identifying relatively underserved and better-served territories, and evaluating how sensitive those conclusions are to alternative weighting definitions.

## Datasets used
- `data/raw/IPRESS_Health_Facilities/IPRESS.csv`
- `data/raw/Consulta_C1_IPRESS/ConsultaC1_2026_v4.csv`
- `data/raw/Populated_Centers/CCPP_IGN100K.shp`
- `data/raw/District_Boundaries_of_Peru/DISTRITOS.shp`

## Repository structure
```text
emergency_access_peru/
├── app.py
├── README.md
├── requirements.txt
├── src/
├── data/
│   ├── raw/
│   └── processed/
├── output/
│   ├── figures/
│   └── tables/
└── video/
    └── link.txt
```

## Data cleaning and preprocessing
Main cleaning decisions implemented in `src/cleaning.py` and supporting modules:
- standardize key text and code fields (`ubigeo`, location names),
- preserve missing and zero emergency activity values for traceability,
- create score-ready filled numeric fields (`*_for_score`) while keeping raw quality flags,
- fix IPRESS coordinate interpretation (`NORTE` as longitude, `ESTE` as latitude),
- create GeoDataFrames and assign points to districts using spatial joins,
- use projected CRS (EPSG:3857) for distance calculations in kilometers.

Processed outputs are saved under `data/processed/`.

## District-level metrics and framework
Implemented in `src/metrics.py`.

1. Q1 Territorial Availability
- Facility component: all facilities + emergency-capable proxy facilities (`I-4`, `II-1`, `II-2`, `II-E`, `III-1`, `III-2`, `III-E`).
- Activity component: emergency attentions and attended counts.
- Scaling: `log1p` + min-max scaling.
- Final score: weighted average of facility and activity components.

2. Q2 Settlement Access
- For each populated center, nearest emergency-capable facility distance is computed.
- District component includes:
  - distance performance (lower median distance is better),
  - populated-center coverage share.
- Final score: weighted combination of distance and coverage.

3. Q3 Combined District Comparison (baseline)
- `Q3 = 0.50 * Q1 + 0.50 * Q2`.

4. Q4 Methodological Sensitivity (alternative)
- `Q4 = 0.30 * facility_component + 0.20 * activity_component + 0.50 * Q2`.
- Compare Q3 vs Q4 using rank shifts per district.

## Static and interactive outputs
Static outputs (`matplotlib` / `seaborn`) are saved in `output/figures/` and district tables in `output/tables/`.

Interactive exploration is available in Streamlit Tab 4 using Folium district maps for:
- baseline combined score,
- alternative combined score,
- rank shift (alternative vs baseline),
- Q1 and Q2 scores.

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

## What Streamlit pipeline buttons should do
In the sidebar:
- `Run Q1 pipeline`: rebuilds Q1 tables/figures.
- `Run Q2 pipeline`: rebuilds Q2 geospatial access tables/figures.
- `Run Q3 + Q4 pipeline`: rebuilds combined baseline/alternative comparison and sensitivity outputs.

After each run, the app clears cache for that block and refreshes visuals/tables.

## Main findings (current outputs)
From generated summaries in `output/tables/`:
- Q1 table contains 1,874 districts and keeps data quality mapping (missing/zero tracking).
- Q2 evaluates 1,873 districts, 136,369 populated centers, and 596 emergency-related facilities with valid coordinates.
- Q3/Q4 combined table currently has 1,885 districts after outer-join consolidation.
- Baseline top districts include MIRAFLORES, AREQUIPA, and LIMA.
- Sensitivity is material in many districts: mean absolute rank shift is about `21.70`, with a maximum observed shift of `193`.

## Why these graphs were selected
- Top/bottom bar charts support direct district comparison for decision-making.
- Scatter and distribution charts reveal scale effects and skewness better than only tabular ranks.
- Rank-shift histogram directly answers methodological sensitivity (Q4), which a simple top-10 list cannot show.
- Choropleth map enables territorial pattern detection and local comparison by department.

## Main limitations
- District counts differ slightly across Q1/Q2/Q3-Q4 due to source coverage and outer-join integration.
- Some activity fields contain placeholders/non-numeric values, handled as missing and tracked.
- Distance-based access is nearest-facility only; it does not model travel-time friction or referral pathways.
- Geometry quality and administrative coding consistency in source files can affect district matching.

## Reproducibility notes
- Keep raw files under the expected `data/raw/` subfolders.
- Run pipelines before opening the app if outputs do not exist yet.
- If you update raw data, re-run all three pipelines in sequence.
