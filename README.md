# Deforestation Detection from Sentinel-2 Imagery

Detecting newly cleared forest using free Sentinel-2 satellite imagery, a
U-Net segmentation model that maps forest cover, and change detection between
dates that flags new clearings on an interactive map.

**Status:** in progress (30-day build, currently on Day 12)
| 11 | Label sources, forest definition, label download and agreement | yes |

## Approach

1. Build clean, cloud-free median composites of Sentinel-2 L2A for two dates
2. Train a U-Net to classify each pixel as forest or non-forest
3. Compare the forest maps of both dates (post-classification change detection)
4. Clean the result and export clearing polygons with area in hectares
5. Show results on an interactive map and web app

## Study area

A 25 x 25 km square in Rondonia, Brazil, built in UTM zone 20S (EPSG:32720)
so that it is a true square on the ground. Defined in `aoi/aoi.geojson`.

Time windows (same season, to avoid detecting seasonal change):
- Period A: 2022-06-01 to 2022-09-30
- Period B: 2024-06-01 to 2024-09-30 (may change if smoke haze is a problem)

## Setup

```bash
conda create -n deforest python=3.11 -y
conda activate deforest
conda install -c conda-forge rasterio geopandas shapely pyproj rioxarray xarray dask jupyterlab matplotlib scikit-image scipy pyyaml -y
pip install pystac-client planetary-computer stackstac odc-stac
pip install torch torchvision segmentation-models-pytorch albumentations
pip install leafmap folium streamlit streamlit-folium
```

Check the environment and configuration:

```bash
python check_env.py
python src/make_aoi.py
python src/check_config.py
```

All settings (bbox, CRS, dates, resolution) live in `config.yaml`.

## Project structure

```
aoi/          study area polygon
data/         rasters (not tracked by Git)
models/       trained weights (not tracked)
outputs/      figures and maps (not tracked)
src/          scripts
config.yaml   single source of truth for settings
```

## Progress log

| Day | Topic | Done |
|---|---|---|
| 1 | Environment, AOI, configuration | yes |
| 2 | Rasters: CRS, transform, nodata, resampling, reprojection, clipping | yes |
| 3 | Vectors, polygonize, rasterize | yes |
| 4-6 | Sentinel-2 via STAC, bands, NDVI baseline | yes|
| 7-14 | Cloud masking, composites, labels, Random Forest baseline | day 11 done |
| 15-21 | Tiling, U-Net, training, evaluation | |
| 22-27 | Change detection, post-processing, validation | |
| 28-30 | Interactive map, Streamlit app, documentation | |

## Key lessons so far

- GeoJSON and shapely use (longitude, latitude) order
- Measure areas in a projected CRS (UTM, meters), never in degrees
- Mask nodata before computing statistics
- Resample labels with nearest neighbor, continuous data with bilinear
- Reproject as little as possible
- STAC: Catalog > Collection > Item > Asset; read only the window you need from COGs
- L2A reflectance = (DN - 1000) / 10000 for processing baseline >= 04.00; DN 0 = no data
- Scene-level cloud cover is only a coarse filter; pixel-level masking comes next
- The real Sentinel-2 grid (origin on multiples of 10 m) is the master grid
- Differencing assumes nothing but land change differs between dates; haze, phenology, processing baseline and shadows all break it
- Null experiment: difference two scenes 10 days apart to get a false-alarm floor; it underestimates the multi-year problem
- A one-sided decrease/increase ratio fits both deforestation and a year-wide drying, so it is not proof of clearing
- AOT (aerosol optical thickness) measures smoke directly; scene cloud cover does not
- A bound is not an estimate: 886 ha is the most this method could call loss, not what was lost
- Name outputs after their parameters so later runs never overwrite earlier results
- Lazy loading (xarray + Dask + odc-stac): build the graph first, compute only what you need
- Sign URLs at read time (patch_url) when loading lazily; links expire
- Deduplicate by (date, tile), keep the newest processing baseline
- Define the master grid explicitly (snap outward to 10 m multiples), then verify against old data
- Dilate cloud masks using evidence (blue vs distance to cloud), not a guessed number
- Select scenes by haze (AOT), never by the result you are measuring
- Build both composites with identical settings; verify alignment by script (metadata, tags, phase correlation)
- Phase cross-correlation estimates sub-pixel misregistration between two dates
- Compare composite noise with the single-date noise measured earlier (Day 6) before trusting a method
- Never tune thresholds from a comparison of the two years; wait for independent labels
- Weak labels come from other people's models: measure their agreement with each other before training on them
- Match label dates to image dates; ambiguous timing becomes an "ignore" value, not a guess
- Fix the forest definition from convention before looking at sweeps, or the result is circular
- Hansen loss year Y is a calendar year; it can fall before or after a June-July composite