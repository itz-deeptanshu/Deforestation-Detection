import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap
from scipy import ndimage

from config import ROOT, load_config
from scene_io import compute_ndvi, load_saved_scene

PIXEL_HA = 0.01
ZOOM = (1700, 2200, 0, 500)     # rows start, rows end, cols start, cols end (change freely)

cfg = load_config()
thr = cfg.get("ndvi_forest_threshold")
if thr is None:
    raise SystemExit("Add 'ndvi_forest_threshold: 0.60' to config.yaml first.")

bands, valid, scl, meta = load_saved_scene()
ndvi = compute_ndvi(bands["B08"], bands["B04"])
ok = valid & np.isfinite(ndvi)
forest = ok & (ndvi > thr)
print(f"Threshold {thr} -> forest {forest.sum() * PIXEL_HA:,.0f} ha "
      f"({forest.sum() / ok.sum() * 100:.1f}% of valid pixels)")

# 1. Save the mask: 1 = forest, 0 = non-forest, 255 = no data
mask = np.where(ok, forest.astype("uint8"), 255).astype("uint8")
out_tif = ROOT / "data" / "raw" / f"s2_{meta['date']}_forest_ndvi.tif"
with rasterio.open(
    out_tif, "w", driver="GTiff",
    height=mask.shape[0], width=mask.shape[1], count=1, dtype="uint8",
    crs=meta["crs"], transform=meta["transform"], nodata=255, compress="deflate",
) as dst:
    dst.write(mask, 1)
print("Saved:", out_tif)

# 2. Fragmentation: connected forest patches (8-connectivity)
labels, n_patches = ndimage.label(forest, structure=np.ones((3, 3)))
sizes = np.bincount(labels.ravel())[1:]          # pixels per patch (skip background 0)
ha = sizes * PIXEL_HA

print(f"\nForest patches        : {n_patches:,}")
print(f"Single-pixel patches  : {(sizes == 1).sum():,}")
print(f"Patches below 0.5 ha  : {(ha < 0.5).sum():,}  (would be removed by the MMU)")
print(f"Largest patch         : {ha.max():,.0f} ha")
print(f"Median patch          : {np.median(ha):.2f} ha")
print(f"Forest area in patches >= 100 ha : {ha[ha >= 100].sum() / ha.sum() * 100:.1f}%")
print(f"Forest area in patches <  5 ha   : {ha[ha < 5].sum() / ha.sum() * 100:.1f}%")

# 3. Figure: false color | forest mask | zoom with the boundary drawn
def stretch(a, lo, hi):
    return np.nan_to_num(np.clip((a - lo) / (hi - lo), 0, 1))

false_color = np.dstack([
    stretch(bands["B08"], 0, 0.5),
    stretch(bands["B04"], 0, 0.2),
    stretch(bands["B03"], 0, 0.2),
])
display_mask = np.where(ok, forest, 2)           # 0 other, 1 forest, 2 no data
r0, r1, c0, c1 = ZOOM

fig, axes = plt.subplots(1, 3, figsize=(20, 7))
axes[0].imshow(false_color)
axes[0].set_title("False color (NIR, Red, Green)")

axes[1].imshow(display_mask, cmap=ListedColormap(["#d9c58b", "#1f7a2e", "#000000"]),
               vmin=0, vmax=2, interpolation="nearest")
axes[1].set_title(f"NDVI > {thr}  (green = forest)")

axes[2].imshow(false_color[r0:r1, c0:c1])
axes[2].contour(forest[r0:r1, c0:c1].astype(float), levels=[0.5],
                colors="yellow", linewidths=0.8)
axes[2].set_title(f"Zoom rows {r0}-{r1}, cols {c0}-{c1} with forest boundary")

for ax in axes:
    ax.axis("off")
fig.tight_layout()
out_png = ROOT / "outputs" / "day5_forest_ndvi.png"
fig.savefig(out_png, dpi=110)
print("\nSaved figure:", out_png)
plt.show()