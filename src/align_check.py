import numpy as np
import rasterio
from skimage.registration import phase_cross_correlation

from config import ROOT, load_config
from stack_utils import master_geobox

cfg = load_config()
gb = master_geobox()
D = ROOT / "data" / "composites"
problems = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label} {detail}")
    if not ok:
        problems.append(label)


info, arrays = {}, {}
for p in ("a", "b"):
    for kind in ("composite", "count"):
        with rasterio.open(D / f"{kind}_{p}.tif") as src:
            info[(kind, p)] = dict(
                crs=src.crs, transform=src.transform, shape=(src.height, src.width),
                count=src.count, dtype=src.dtypes[0], nodata=src.nodata,
                desc=src.descriptions, tags=src.tags(),
            )
            arrays[(kind, p)] = src.read().astype("float32")

# ---------- 1. Metadata ----------
print("--- 1. Metadata ---")
ia, ib = info[("composite", "a")], info[("composite", "b")]
check(ia["crs"] == ib["crs"], "same CRS", str(ia["crs"]))
check(ia["transform"] == ib["transform"], "same transform", f"origin ({ia['transform'].c:.0f}, {ia['transform'].f:.0f})")
check(ia["shape"] == ib["shape"] == tuple(gb.shape), "same shape as master grid", str(ia["shape"]))
check(ia["transform"] == gb.affine, "transform equals master_geobox()")
check(ia["transform"].c % 10 == 0 and ia["transform"].f % 10 == 0, "origin on the 10 m lattice")
check(ia["desc"] == ib["desc"] == ("B02", "B03", "B04", "B08"), "band names", str(ia["desc"]))
check(ia["dtype"] == ib["dtype"] == "float32" and ia["nodata"] == ib["nodata"] == -9999.0, "dtype and nodata")
for p in ("a", "b"):
    check(info[("count", p)]["transform"] == gb.affine and info[("count", p)]["shape"] == tuple(gb.shape),
          f"count_{p} on the master grid")

# ---------- 2. Settings identical ----------
print("\n--- 2. Settings (from file tags) ---")
for key in ("min_clear_obs", "cloud_dilate_px", "scene_aot_max", "units"):
    va, vb = ia["tags"].get(key), ib["tags"].get(key)
    check(va == vb and va is not None, f"tag {key}", f"2022={va} 2024={vb}")
da, db = ia["tags"]["dates"].split(","), ib["tags"]["dates"].split(",")
print(f"  2022 dates ({len(da)}): {da}")
print(f"  2024 dates ({len(db)}): {db}")
check(all(d.startswith("2022") for d in da) and all(d.startswith("2024") for d in db), "dates are in the right years")

# ---------- 3. Valid overlap ----------
print("\n--- 3. Valid pixels ---")
ca, cb = arrays[("composite", "a")], arrays[("composite", "b")]
va = np.isfinite(np.where(ca == -9999.0, np.nan, ca)).all(axis=0)
vb = np.isfinite(np.where(cb == -9999.0, np.nan, cb)).all(axis=0)
print(f"  valid 2022: {va.mean() * 100:.2f}%   valid 2024: {vb.mean() * 100:.2f}%   both: {(va & vb).mean() * 100:.2f}%")
n_a, n_b = arrays[("count", "a")][0], arrays[("count", "b")][0]
print(f"  mean looks 2022: {n_a.mean():.2f} of {len(da)}   2024: {n_b.mean():.2f} of {len(db)}")
check((va & vb).mean() > 0.95, "more than 95% of pixels valid in both years")

# ---------- 4. Sub-pixel co-registration ----------
print("\n--- 4. Co-registration (phase cross-correlation, red band) ---")
def prep(c):
    r = np.where(c[2] == -9999.0, np.nan, c[2])
    return np.nan_to_num(r, nan=float(np.nanmedian(r)))
shift, err, _ = phase_cross_correlation(prep(ca), prep(cb), upsample_factor=20)
print(f"  estimated shift (rows, cols): {shift[0]:+.2f}, {shift[1]:+.2f} pixels")
check(np.abs(shift).max() < 0.5, "shift below half a pixel")

print()
print("ALL ALIGNMENT CHECKS PASSED" if not problems else f"{len(problems)} problem(s): {problems}")