import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from config import ROOT
from scene_io import compute_ndvi, load_saved_scene

SCL_NAMES = {
    0: "no data", 1: "saturated/defective", 2: "dark area", 3: "cloud shadow",
    4: "vegetation", 5: "bare soil", 6: "water", 7: "unclassified",
    8: "cloud (medium)", 9: "cloud (high)", 10: "thin cirrus", 11: "snow/ice",
}
SCL_COLORS = ["#000000", "#ff0000", "#2f2f2f", "#6b4a2b", "#3fa535", "#e8d27a",
              "#1f5fd1", "#8a8a8a", "#c8c8c8", "#ffffff", "#7fd8ff", "#ff7fe8"]

bands, valid, scl, meta = load_saved_scene()
print("Scene  :", meta["path"].name)
print("Offset :", meta["offset"])

# 1. NDVI
ndvi = compute_ndvi(bands["B08"], bands["B04"])

print("\nNDVI percentiles over valid pixels")
labels = ["min", "p2", "p25", "median", "p75", "p98", "max"]
for lab, v in zip(labels, np.nanpercentile(ndvi, [0, 2, 25, 50, 75, 98, 100])):
    print(f"  {lab:7s} {v:6.3f}")

# 2. NDVI inside each SCL class
print("\nNDVI by SCL class")
print("class                    % pixels    mean     p5     p95")
for v in np.unique(scl[valid]):
    sel = valid & (scl == v) & np.isfinite(ndvi)
    vals = ndvi[sel]
    p5, p95 = np.percentile(vals, [5, 95])
    print(f"{v:2d} {SCL_NAMES[int(v)]:20s} {sel.sum() / valid.sum() * 100:8.2f} "
          f"{vals.mean():7.3f} {p5:7.3f} {p95:7.3f}")

veg = valid & (scl == 4) & np.isfinite(ndvi)
share_low = np.mean(ndvi[veg] < 0.6) * 100
print(f"\nSCL 'vegetation' pixels with NDVI < 0.6: {share_low:.1f}%")
print("-> SCL class 4 is NOT the same as forest.")

# 3. Save NDVI as a GeoTIFF (nodata = -9999, as on Day 2)
out_tif = ROOT / "data" / "raw" / f"s2_{meta['date']}_ndvi.tif"
with rasterio.open(
    out_tif, "w", driver="GTiff",
    height=ndvi.shape[0], width=ndvi.shape[1], count=1, dtype="float32",
    crs=meta["crs"], transform=meta["transform"], nodata=-9999.0,
    compress="deflate", tiled=True, blockxsize=256, blockysize=256,
) as dst:
    dst.write(np.nan_to_num(ndvi, nan=-9999.0).astype("float32"), 1)
print("\nSaved:", out_tif)

# 4. Plot NDVI and SCL side by side
fig, axes = plt.subplots(1, 2, figsize=(15, 7))

im = axes[0].imshow(np.ma.masked_invalid(ndvi), cmap="RdYlGn", vmin=0, vmax=1)
axes[0].set_title(f"NDVI  {meta['date']}")
fig.colorbar(im, ax=axes[0], shrink=0.75, label="NDVI")

axes[1].imshow(scl, cmap=ListedColormap(SCL_COLORS), vmin=0, vmax=11,
               interpolation="nearest")
present = [int(v) for v in np.unique(scl)]
axes[1].legend(
    handles=[Patch(color=SCL_COLORS[v], label=f"{v} {SCL_NAMES[v]}") for v in present],
    loc="lower left", fontsize=8, framealpha=0.9,
)
axes[1].set_title("Scene Classification Layer (SCL)")

for ax in axes:
    ax.axis("off")
fig.tight_layout()
out_png = ROOT / "outputs" / "day5_ndvi_scl.png"
fig.savefig(out_png, dpi=110)
print("Saved figure:", out_png)
plt.show()