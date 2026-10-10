# Deforestation Detection from Sentinel-2 Imagery

Detecting newly cleared forest using free Sentinel-2 satellite imagery, a
U-Net segmentation model that maps forest cover, and change detection between
dates that flags new clearings on an interactive map.

**Status:** in progress (30-day build, currently on Day 3)

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
| 3 | Vectors, polygonize, rasterize | |
| 4-6 | Sentinel-2 via STAC, bands, NDVI baseline | |
| 7-14 | Cloud masking, composites, labels, Random Forest baseline | |
| 15-21 | Tiling, U-Net, training, evaluation | |
| 22-27 | Change detection, post-processing, validation | |
| 28-30 | Interactive map, Streamlit app, documentation | |

## Key lessons so far

- GeoJSON and shapely use (longitude, latitude) order
- Measure areas in a projected CRS (UTM, meters), never in degrees
- Mask nodata before computing statistics
- Resample labels with nearest neighbor, continuous data with bilinear
- Reproject as little as possible