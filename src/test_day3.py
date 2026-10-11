import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize, shapes
from shapely.geometry import box, shape

from config import ROOT

with rasterio.open(ROOT / "data" / "raw" / "toy_ndvi_utm.tif") as src:
    ndvi, nodata = src.read(1), src.nodata
    transform, crs, bounds = src.transform, src.crs, src.bounds

# Rebuild the Day 3 mask exactly as polygonize_mask.py did
cleared = (ndvi != nodata) & (ndvi < 0.5)
assert int(cleared.sum()) == 470_000, cleared.sum()
cleared[2000:2003, 1500:1503] = True
cleared[2200, 2200] = True
mask = cleared.astype("uint8")

# 1. Polygonize
geoms = [shape(g) for g, v in shapes(mask, mask=mask, transform=transform, connectivity=4)]
gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs)
gdf["area_ha"] = gdf.area / 10_000
gdf = gdf.sort_values("area_ha", ascending=False).reset_index(drop=True)
print("Polygon areas (ha):", gdf.area_ha.round(2).tolist())
assert len(gdf) == 4
assert np.allclose(gdf.area_ha, [3200, 1500, 0.09, 0.01], atol=0.001)
print("[PASS] polygonize: 4 polygons with exact areas")

# 2. MMU
kept = gdf[gdf.area_ha >= 0.5]
assert len(kept) == 2
print("[PASS] MMU keeps 2, removes 2 speckles")

# 3. Rasterize round trip
burned = rasterize([(g, 1) for g in gdf.geometry], out_shape=ndvi.shape,
                   transform=transform, fill=0, dtype="uint8")
mismatch = int((burned != mask).sum())
assert mismatch == 0, mismatch
print("[PASS] rasterize round trip: 0 mismatching pixels")

# 4. Overlay vs sjoin
reserve = gpd.GeoDataFrame(
    {"name": ["Toy Reserve"]},
    geometry=[box(bounds.left + 10_000, bounds.bottom, bounds.left + 20_000, bounds.top)],
    crs=crs)
inside = gpd.overlay(kept, reserve, how="intersection")
inside_ha = inside.geometry.area.sum() / 10_000
assert abs(inside_ha - 1600) < 0.01, inside_ha
share = inside_ha / kept.area_ha.sum() * 100
assert abs(share - 34.0) < 0.1, share
print(f"[PASS] overlay: {inside_ha:.0f} ha inside reserve ({share:.1f}%)")

joined = gpd.sjoin(kept, reserve, how="left", predicate="intersects")
tagged_ha = joined.loc[joined["name"].notna(), "area_ha"].sum()
assert abs(tagged_ha - 3200) < 0.01
print(f"[PASS] sjoin tags the whole 3200 ha clearing (overcounts by {tagged_ha - inside_ha:.0f} ha)")

# 5. Area in the wrong CRS
deg = gdf.to_crs(4326)
assert deg.area.iloc[0] < 0.01
print(f"[PASS] same 3200 ha polygon has 'area' {deg.area.iloc[0]:.5f} in EPSG:4326 (meaningless)")

print("\nDay 3 code verified.")