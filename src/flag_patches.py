import argparse

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from scipy import ndimage
from shapely.geometry import shape

from config import ROOT
from scene_io import compute_ndvi, load_saved_scene

PIXEL_HA = 0.01

parser = argparse.ArgumentParser()
parser.add_argument("--a", default="2022-07-09")
parser.add_argument("--b", default="2024-07-13")
parser.add_argument("--drop", type=float, default=0.25)
parser.add_argument("--top", type=int, default=15)
args = parser.parse_args()

stem = f"change_{args.a}_{args.b}_drop{args.drop}"
with rasterio.open(ROOT / "data" / "raw" / f"{stem}_flag.tif") as src:
    mask = src.read(1) == 1                 # 1 = flagged, 0 = not, 255 = no data
    transform, crs = src.transform, src.crs

ndvi_a = compute_ndvi(*[load_saved_scene(args.a)[0][k] for k in ("B08", "B04")])
ndvi_b = compute_ndvi(*[load_saved_scene(args.b)[0][k] for k in ("B08", "B04")])

# One label per 8-connected patch, then per-patch statistics
labels, n = ndimage.label(mask, structure=np.ones((3, 3)))
ids = np.arange(1, n + 1)
area_ha = ndimage.sum(mask, labels, ids) * PIXEL_HA
mean_a = ndimage.mean(ndvi_a, labels, ids)
mean_b = ndimage.mean(ndvi_b, labels, ids)

# One polygon per patch
polys = {}
for geom, value in shapes(labels.astype("int32"), mask=mask,
                          transform=transform, connectivity=8):
    polys[int(value)] = shape(geom)

gdf = gpd.GeoDataFrame(
    {"patch": ids, "area_ha": area_ha, "ndvi_a": mean_a, "ndvi_b": mean_b},
    geometry=[polys[i] for i in ids], crs=crs,
)
gdf["drop"] = gdf.ndvi_b - gdf.ndvi_a
cent = gdf.geometry.centroid.to_crs(epsg=4326)
gdf["lon"], gdf["lat"] = cent.x, cent.y
gdf = gdf.sort_values("area_ha", ascending=False).reset_index(drop=True)

cols = ["patch", "area_ha", "ndvi_a", "ndvi_b", "drop", "lon", "lat"]
print(f"Patches: {len(gdf)} | total {gdf.area_ha.sum():,.0f} ha | "
      f"median {gdf.area_ha.median():.2f} ha | largest {gdf.area_ha.max():.1f} ha")
print("\nLargest patches")
print(gdf[cols].head(args.top).round(3).to_string(index=False))
print("\nRandom sample of 10 (use this one for your unbiased tally)")
print(gdf[cols].sample(min(10, len(gdf)), random_state=0).round(3).to_string(index=False))

q = gdf.ndvi_a.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(3).tolist()
amb = gdf.loc[gdf.ndvi_a < 0.72, "area_ha"].sum() / gdf.area_ha.sum() * 100
print(f"\nNDVI at A of flagged patches, p10/p25/p50/p75/p90: {q}")
print(f"Share of flagged area with NDVI_A below 0.72 (ambiguous zone): {amb:.1f}%")

out = ROOT / "outputs" / f"{stem}_patches.gpkg"
gdf.to_file(out, driver="GPKG")
print("Saved:", out)