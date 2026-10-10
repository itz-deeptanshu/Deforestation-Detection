import glob

import geopandas as gpd
import numpy as np
import rasterio
from shapely.geometry import box

from config import ROOT, load_config

cfg = load_config()
files = sorted(glob.glob(str(ROOT / "data" / "raw" / "s2_*_aoi.tif")))
if not files:
    raise SystemExit("Run load_scene.py first.")
path = files[-1]
print("Checking:", path)

with rasterio.open(path) as src:
    print("\nCRS        :", src.crs)
    print("Shape      :", src.count, "bands x", src.height, "rows x", src.width, "cols")
    print("Dtype      :", src.dtypes[0], "| nodata:", src.nodata)
    print("Pixel size :", src.res)
    print("Band names :", src.descriptions)
    print("Tags       :", src.tags())

    t = src.transform
    print("\nGrid origin (x, y)      :", t.c, t.f)
    print("Origin x mod 10, y mod 10:", round(t.c % 10, 6), round(t.f % 10, 6))

    raster_box = box(*src.bounds)
    data = src.read(1)

# Does the raster cover the AOI?
aoi = gpd.read_file(ROOT / cfg["aoi_path"]).to_crs(src.crs).geometry.iloc[0]
covered = aoi.intersection(raster_box).area / aoi.area
print(f"\nAOI covered by raster: {covered * 100:.2f}%")
print("Raster extent / AOI area:", round(raster_box.area / aoi.area, 4))
print("Nodata pixels in band 1 :", int((data == 0).sum()))

# Compare with the Day 2 toy grid
with rasterio.open(ROOT / "data" / "raw" / "toy_ndvi_utm.tif") as toy:
    dx = toy.transform.c - t.c
    dy = toy.transform.f - t.f
print(f"\nToy grid origin minus real grid origin: dx={dx:.2f} m, dy={dy:.2f} m")
print("-> From now on the real Sentinel-2 grid is the master grid.")