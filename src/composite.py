import argparse

import numpy as np
import rasterio

from composite_utils import BANDS, build_composite, selected_dates
from config import ROOT, load_config
from stack_utils import master_geobox

parser = argparse.ArgumentParser()
parser.add_argument("--period", choices=["a", "b"], required=True)
args = parser.parse_args()

cfg = load_config()
name = f"period_{args.period}"
min_obs = cfg["min_clear_obs"]
dates = selected_dates(name)
print(f"{name}: compositing {len(dates)} dates, min_clear_obs = {min_obs}")

comp, count, rows = build_composite(dates, min_obs)

gb = master_geobox()
assert comp.shape[1:] == tuple(gb.shape), "composite is not on the master grid"

# ---------- Per-date table ----------
print("\ndate         good%   NDVI median   forest%")
for r in rows:
    print(f"{r['date']}  {r['good_pct']:6.1f}   {r['ndvi_med']:9.3f}   {r['forest_pct']:7.2f}")

# ---------- Count map ----------
print("\nGood observations per pixel")
total = count.size
for k in range(len(dates) + 1):
    print(f"  {k} looks: {(count == k).sum() / total * 100:6.2f}%")
print(f"  mean {count.mean():.2f}, median {np.median(count):.0f}")
below = (count < min_obs).mean() * 100
print(f"  pixels below min_clear_obs ({min_obs}): {below:.3f}%  (set to NaN)")

# ---------- Composite statistics ----------
print("\nComposite reflectance (valid pixels)")
for b, nm in enumerate(BANDS):
    v = comp[b][np.isfinite(comp[b])]
    print(f"  {nm}: median {np.median(v):.4f}  p1 {np.percentile(v, 1):.4f}  p99 {np.percentile(v, 99):.4f}")

# ---------- Save ----------
out_dir = ROOT / "data" / "composites"
out_dir.mkdir(parents=True, exist_ok=True)
profile = dict(
    driver="GTiff", height=comp.shape[1], width=comp.shape[2],
    crs=f"EPSG:{cfg['utm_epsg']}", transform=gb.affine,
    compress="deflate", tiled=True, blockxsize=256, blockysize=256,
)
with rasterio.open(out_dir / f"composite_{args.period}.tif", "w",
                   count=4, dtype="float32", nodata=-9999.0, **profile) as dst:
    dst.write(np.where(np.isfinite(comp), comp, -9999.0).astype("float32"))
    dst.descriptions = tuple(BANDS)
    dst.update_tags(dates=",".join(dates), min_clear_obs=str(min_obs),
                    cloud_dilate_px=str(cfg["cloud_dilate_px"]),
                    scene_aot_max=str(cfg["scene_aot_max"]),
                    units="surface reflectance 0-1, offset already applied")
with rasterio.open(out_dir / f"count_{args.period}.tif", "w",
                   count=1, dtype="uint8", **profile) as dst:
    dst.write(count, 1)

print("\nSaved:", out_dir / f"composite_{args.period}.tif")
print("Saved:", out_dir / f"count_{args.period}.tif")