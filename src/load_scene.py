import matplotlib.pyplot as plt
import numpy as np
import rasterio
from shapely.geometry import shape

from config import ROOT, load_config
from s2_utils import load_aoi_4326, read_band, read_on_grid, search_items

cfg = load_config()
period = cfg["period_a"]
BANDS = ["B02", "B03", "B04", "B08"]          # blue, green, red, NIR (all 10 m)

SCL_NAMES = {
    0: "no data", 1: "saturated/defective", 2: "dark area", 3: "cloud shadow",
    4: "vegetation", 5: "bare soil", 6: "water", 7: "unclassified",
    8: "cloud (medium)", 9: "cloud (high)", 10: "thin cirrus", 11: "snow/ice",
}

# ---------- 1. Choose a scene ----------
aoi = load_aoi_4326()
items = search_items(period["start"], period["end"], cfg["max_scene_cloud_pct"])
items = [it for it in items if shape(it.geometry).contains(aoi)]
if not items:
    raise SystemExit("No scene fully covers the AOI (it may span two tiles). "
                     "Tell me and we will handle mosaicking.")

best = min(items, key=lambda it: it.properties["eo:cloud_cover"])
date = best.properties["datetime"][:10]
tile = best.properties.get("s2:mgrs_tile", "tile")
baseline = float(best.properties.get("s2:processing_baseline", "0"))
offset = 1000 if baseline >= 4.0 else 0

print(f"Chosen scene : {best.id}")
print(f"Date / tile  : {date} / {tile}")
print(f"Scene cloud  : {best.properties['eo:cloud_cover']:.1f}%")
print(f"Baseline     : {baseline}  ->  offset to subtract = {offset}")

# ---------- 2. Read the four 10 m bands, clipped to the AOI ----------
arrays = []
for b in BANDS:
    print("Reading", b, "...")
    arr, transform, crs = read_band(best.assets[b].href)
    arrays.append(arr)
dn = np.stack(arrays)                          # shape (4, rows, cols), uint16
print("Stack shape  :", dn.shape, "| dtype:", dn.dtype, "| CRS:", crs)

# ---------- 3. SCL (20 m) resampled to our 10 m grid ----------
scl = read_on_grid(best.assets["SCL"].href, dn.shape[1:], transform, crs)

# ---------- 4. Convert to reflectance, masking no-data FIRST ----------
valid = (dn > 0).all(axis=0)
refl = (dn.astype("float32") - offset) / 10000.0
refl[:, ~valid] = np.nan
print(f"Valid pixels : {valid.mean() * 100:.2f}%")

print("\nReflectance statistics over valid pixels")
print("band    min     p2   median    p98     max")
for name, band in zip(BANDS, refl):
    q = np.nanpercentile(band, [0, 2, 50, 98, 100])
    print(f"{name}  {q[0]:6.3f} {q[1]:6.3f} {q[2]:7.3f} {q[3]:7.3f} {q[4]:7.3f}")

# ---------- 5. SCL composition (preview of Day 5) ----------
print("\nSCL classes (% of valid pixels)")
vals, counts = np.unique(scl[valid], return_counts=True)
for v, c in zip(vals, counts):
    print(f"  {v:2d} {SCL_NAMES.get(int(v), '?'):20s} {c / valid.sum() * 100:6.2f}%")

# ---------- 6. Save the clipped scene as GeoTIFFs ----------
h, w = dn.shape[1:]
out_dir = ROOT / "data" / "raw"
out_dir.mkdir(parents=True, exist_ok=True)
stem = f"s2_{date}_{tile}"

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

print("\nSaved:", out_dir / f"{stem}_aoi.tif")
print("Saved:", out_dir / f"{stem}_scl.tif")

# ---------- 7. Plot four ways ----------
def stretch(img, lo, hi):
    out = np.clip((img - lo) / (hi - lo), 0, 1)
    return np.nan_to_num(out, nan=0.0)         # no-data shows as black

red, green, blue, nir = refl[2], refl[1], refl[0], refl[3]

naive = np.dstack([stretch(red, 0, 1), stretch(green, 0, 1), stretch(blue, 0, 1)])
fixed = np.dstack([stretch(red, 0, 0.3), stretch(green, 0, 0.3), stretch(blue, 0, 0.3)])

lo_hi = [np.nanpercentile(b, [2, 98]) for b in (red, green, blue)]
pct = np.dstack([stretch(b, lo, hi) for b, (lo, hi) in zip((red, green, blue), lo_hi)])

false_color = np.dstack([stretch(nir, 0, 0.5), stretch(red, 0, 0.2), stretch(green, 0, 0.2)])

fig, axes = plt.subplots(2, 2, figsize=(12, 12))
panels = [
    (naive, "True color, stretch 0-1 (too dark)"),
    (fixed, "True color, fixed stretch 0-0.3"),
    (pct, "True color, percentile 2-98 stretch"),
    (false_color, "False color (NIR, Red, Green)"),
]
for ax, (img, title) in zip(axes.ravel(), panels):
    ax.imshow(img)
    ax.set_title(title)
    ax.axis("off")
fig.suptitle(f"Sentinel-2 L2A  {date}  tile {tile}", fontsize=14)
fig.tight_layout()

out_png = ROOT / "outputs" / "day4_scene.png"
fig.savefig(out_png, dpi=110)
print("Saved figure:", out_png)
plt.show()