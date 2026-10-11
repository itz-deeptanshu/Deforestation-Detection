import argparse
from datetime import date as Date
from datetime import timedelta

import numpy as np
import rasterio
from shapely.geometry import shape

from config import ROOT
from s2_utils import load_aoi_4326, read_band, read_on_grid, search_items

BANDS = ["B02", "B03", "B04", "B08"]

parser = argparse.ArgumentParser(description="Save one Sentinel-2 scene clipped to the AOI.")
parser.add_argument("--date", required=True, help="acquisition date, e.g. 2024-07-13")
args = parser.parse_args()

day = Date.fromisoformat(args.date)
aoi = load_aoi_4326()

# 1. Search one day (end date is the next day; we filter exactly afterwards)
items = search_items(day.isoformat(), (day + timedelta(days=1)).isoformat(), 101)
items = [
    it for it in items
    if it.properties["datetime"][:10] == args.date and shape(it.geometry).contains(aoi)
]
if not items:
    raise SystemExit(f"No scene covering the AOI on {args.date}. Pick a date from outputs/day4_scenes.csv.")

print("Candidates for", args.date)
for it in items:
    print(f"  {it.id}  baseline {it.properties.get('s2:processing_baseline')}"
          f"  cloud {it.properties['eo:cloud_cover']:.1f}%")

# 2. If the date exists in two baselines, prefer the newest
best = max(items, key=lambda it: float(it.properties.get("s2:processing_baseline", "0")))
tile = best.properties.get("s2:mgrs_tile", "tile")
baseline = float(best.properties.get("s2:processing_baseline", "0"))
offset = 1000 if baseline >= 4.0 else 0
print(f"\nChosen   : {best.id}")
print(f"Baseline : {baseline} -> offset {offset}")

# 3. Read bands and SCL
dn = np.stack([read_band(best.assets[b].href)[0] for b in BANDS])
_, transform, crs = read_band(best.assets["B04"].href)
scl = read_on_grid(best.assets["SCL"].href, dn.shape[1:], transform, crs)
print("Shape    :", dn.shape, "| origin:", transform.c, transform.f)

# 4. Save
h, w = dn.shape[1:]
out_dir = ROOT / "data" / "raw"
stem = f"s2_{args.date}_{tile}"
profile = dict(
    driver="GTiff", height=h, width=w, crs=crs, transform=transform,
    compress="deflate", tiled=True, blockxsize=256, blockysize=256,
)

with rasterio.open(out_dir / f"{stem}_aoi.tif", "w",
                   count=4, dtype="uint16", nodata=0, **profile) as dst:
    dst.write(dn)
    dst.descriptions = tuple(BANDS)
    dst.update_tags(item_id=best.id, processing_baseline=str(baseline),
                    boa_offset=str(offset), scale="10000")

with rasterio.open(out_dir / f"{stem}_scl.tif", "w",
                   count=1, dtype="uint8", **profile) as dst:
    dst.write(scl, 1)

# 5. Optional: aerosol optical thickness (for the smoke check)
try:
    aot, t_aot, _ = read_band(best.assets["AOT"].href)
    if aot.shape == (h, w) and t_aot == transform:
        with rasterio.open(out_dir / f"{stem}_aot.tif", "w",
                           count=1, dtype="uint16", nodata=0, **profile) as dst:
            dst.write(aot, 1)
        print("AOT saved (scale 0.001)")
    else:
        print("AOT skipped: not on the 10 m grid, shape", aot.shape)
except Exception as exc:
    print("AOT skipped:", exc)

print("Saved    :", out_dir / f"{stem}_aoi.tif")