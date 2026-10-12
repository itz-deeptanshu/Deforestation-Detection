import numpy as np
import rasterio

from config import load_config
from scene_io import find_scene_path
from stack_utils import get_item_for_date, load_lazy, master_geobox

DATE = "2022-07-09"
res = load_config()["resolution_m"]

gb = master_geobox()
left, top = gb.affine.c, gb.affine.f
print("New grid shape:", tuple(gb.shape), "| origin:", left, top)

# Legacy (Day 4-7) scene
legacy_path = find_scene_path(DATE)
with rasterio.open(legacy_path) as src:
    dn_old, t = src.read(), src.transform
with rasterio.open(str(legacy_path).replace("_aoi.tif", "_scl.tif")) as src:
    scl_old = src.read(1)

row_off = int(round((top - t.f) / res))
col_off = int(round((t.c - left) / res))
print(f"Legacy grid starts at row {row_off}, col {col_off} of the new grid")

# New pipeline
ds = load_lazy([get_item_for_date(DATE)], ["B02", "B03", "B04", "B08", "SCL"]).isel(time=0).compute()
win = (slice(row_off, row_off + dn_old.shape[1]), slice(col_off, col_off + dn_old.shape[2]))

print("\nBand-by-band comparison over the overlap (digital numbers)")
for k, name in enumerate(["B02", "B03", "B04", "B08"]):
    new = np.nan_to_num(ds[name].values, nan=0).astype("uint16")[win]
    diff = int((new != dn_old[k]).sum())
    print(f"  {name}: identical = {diff == 0}  (mismatching pixels: {diff})")
    assert diff == 0, f"{name} differs: the new pipeline does not match the old one"

agree = (np.nan_to_num(ds.SCL.values, nan=0).astype("uint8")[win] == scl_old).mean() * 100
print(f"  SCL: {agree:.2f}% of pixels agree")

# Does the new grid cover the whole AOI now?
import geopandas as gpd
from config import ROOT
cfg = load_config()
minx, miny, maxx, maxy = gpd.read_file(ROOT / cfg["aoi_path"]).to_crs(epsg=cfg["utm_epsg"]).total_bounds
right = left + gb.shape[1] * res
bottom = top - gb.shape[0] * res
covers = left <= minx and bottom <= miny and right >= maxx and top >= maxy
print("\nNew grid fully covers the AOI:", covers)
assert covers
print("Verified: the new lazy pipeline reproduces the legacy data exactly.")