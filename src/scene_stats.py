import numpy as np
import rasterio

from config import ROOT, load_config
from scene_io import compute_ndvi, find_scene_path, load_saved_scene

thr = load_config()["ndvi_forest_threshold"]
dates = sorted({p.name.split("_")[1] for p in (ROOT / "data" / "raw").glob("s2_20*_aoi.tif")})

rows = []
for d in dates:
    bands, valid, scl, meta = load_saved_scene(d)
    clear = valid & np.isin(scl, [4, 5])
    ndvi = compute_ndvi(bands["B08"], bands["B04"])
    ok = clear & np.isfinite(ndvi)

    with rasterio.open(find_scene_path(d)) as src:
        baseline = src.tags().get("processing_baseline", "?")
    aot_file = str(find_scene_path(d)).replace("_aoi.tif", "_aot.tif")
    try:
        with rasterio.open(aot_file) as s:
            a = s.read(1).astype("float32") / 1000
        aot = float(np.median(a[a > 0]))
    except Exception:
        aot = float("nan")

    rows.append(dict(
        date=d, base=baseline, clear=clear.mean() * 100,
        blue=float(np.median(bands["B02"][clear])),
        blue_p1=float(np.percentile(bands["B02"][clear], 1)),
        red=float(np.median(bands["B04"][clear])),
        nir=float(np.median(bands["B08"][clear])),
        ndvi=float(np.median(ndvi[ok])),
        forest=float((ndvi[ok] > thr).mean() * 100),
        aot=aot,
    ))

print("date        base  clear%  blue  blue_p1   red    nir   NDVI_med  forest%   AOT")
for r in rows:
    print(f"{r['date']}  {r['base']:>4}  {r['clear']:6.2f} {r['blue']:6.3f} {r['blue_p1']:7.3f} "
          f"{r['red']:6.3f} {r['nir']:6.3f}  {r['ndvi']:7.3f}  {r['forest']:7.2f}  {r['aot']:5.3f}")

by_year = {}
for r in rows:
    by_year.setdefault(r["date"][:4], []).append(r)
print("\nYear means (of the per-date medians)")
for y, rs in by_year.items():
    print(f"  {y}: n={len(rs)}  blue {np.mean([r['blue'] for r in rs]):.3f}  "
          f"red {np.mean([r['red'] for r in rs]):.3f}  "
          f"NDVI {np.mean([r['ndvi'] for r in rs]):.3f}  "
          f"forest% {np.mean([r['forest'] for r in rs]):.1f}")