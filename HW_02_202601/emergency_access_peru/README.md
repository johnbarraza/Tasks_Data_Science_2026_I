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

This project uses a multidimensional access framing: potential facility availability, geographic proximity, and realized emergency use.

- **Penchansky and Thomas (1981)**. The concept of access: definition and relationship to consumer satisfaction. *Medical Care*, 19(2), 127-140. https://pubmed.ncbi.nlm.nih.gov/7206846/
  Motivates treating access as multidimensional (availability, accessibility, accommodation, affordability, acceptability). Justifies why a single-variable measure is insufficient for this analysis.

- **Luo, W. and Wang, F. (2003)**. Measures of spatial accessibility to health care in a GIS environment: synthesis and a case study in the Chicago region. *Environment and Planning B*, 30(6), 865-884. https://journals.sagepub.com/doi/10.1068/b29120
  Motivates combining service supply and spatial separation in GIS-based access analysis. This project draws on the spatial separation dimension. It does not implement the full 2-Step Floating Catchment Area (2SFCA) method; it uses nearest-facility straight-line distance as a simplified proximity proxy, because population demand by populated center, facility capacity ratios, and catchment delineation are outside the scope of this project.

- **McGrail, M.R. (2012)**. Spatial accessibility of primary health care utilising the two step floating catchment area method: an assessment of recent improvements. *International Journal of Health Geographics*, 11(1), 50. https://link.springer.com/article/10.1186/1476-072X-11-50
  Motivates reporting distance thresholds and spatial isolation tails rather than simple proximity counts. The `share_over_30km` component in Q2 directly applies this principle. The enhanced 2SFCA catchment approach from this paper is not implemented.

- **World Health Organization (2015)**. *WHO Emergency Care System Framework*. https://www.who.int/publications-detail/who-emergency-care-system-framework
  Frames emergency care as a system requiring specific clinical capabilities. Motivates restricting the emergency-facility definition to structural categories I-4, II-*, and III-* rather than using all IPRESS.

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

## Main findings

### Q1 — Territorial availability
- 1,874 districts evaluated. 1,038 (55%) have at least one missing C1 emergency activity row, reflecting widespread under-reporting rather than confirmed absence of care.
- Top-ranked districts by availability: Lima, Arequipa, Miraflores, San Juan de Lurigancho, Trujillo. These concentrate the largest facility counts and highest observed emergency activity.
- Bottom-ranked districts: Cielo Punco, Manitea, Union Ashaninka (Cusco), Boqueron (Ucayali), Santa Lucia (San Martin). Score = 0 driven by missing-dominant C1 activity and near-zero facility presence.

### Q2 — Settlement spatial access
- 136,369 populated centers analyzed across 1,873 districts. 596 structural emergency-proxy facilities with valid coordinates used for distance calculations.
- National average median distance from a populated center to the nearest emergency-proxy facility: **21.4 km**.
- 419 districts (22%) have more than half of their populated centers beyond 30 km from any emergency-proxy facility.
- Best-access districts are dense urban areas: Bellavista/Callao (median 0.15 km), Pueblo Libre, Mariano Melgar. These have few populated centers very close to facilities.
- Worst-access districts are remote Amazonian: Purus/Ucayali (median 229 km), Teniente Manuel Clavero/Loreto (202 km).

### Q3 — Combined baseline score
- Top districts: Miraflores (0.943), Arequipa (0.939), Lima (0.937), Jesus Maria (0.928), San Isidro (0.925). Urban concentration of both supply and observed activity.
- Bottom districts: Santa Lucia, Cielo Punco, Manitea, Cochabamba, Lambras. Score = 0 because missing-dominant C1 activity and weak spatial access compound each other.
- The combined score reveals that districts weak in Q3 fail across all three dimensions simultaneously: low facility presence, no observed emergency activity, and remote populated centers.

### Q4 — Methodological sensitivity
- Mean absolute rank shift between Q3 baseline and Q4 alternative: **189 positions** out of 1,885 districts.
- 742 districts (39%) shift more than 100 positions when the emergency-facility definition changes from structural category to C1-observed activity.
- Largest shift: Vilcabamba, Apurimac — moves from rank 341 (baseline) to rank 1,672 (alternative), a drop of 1,331 positions. This district appears relatively well served under structural categories but has little observed C1 activity reported nearby, suggesting structural registry overestimates realized access.
- Districts that improve under Q4 (e.g., Mancora/Piura: 1,497 to 288) are near facilities that report actual emergency activity even outside the structural emergency-proxy categories.
- **Conclusion**: Results are sensitive to the emergency-facility definition. Neither definition is a ground truth; together they bound the uncertainty in district-level access estimates.

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
- `data/processed/` is not committed to the repository because it is fully regenerated by the pipeline (49 MB of intermediate CSVs). Running the three pipeline commands above recreates all processed files before the app loads them.
