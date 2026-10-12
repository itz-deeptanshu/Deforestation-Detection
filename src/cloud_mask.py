import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from scipy import ndimage

from config import ROOT, load_config
from scene_io import compute_ndvi
from stack_utils import get_item_for_date, load_lazy, to_reflectance

SCL_NAMES = {0: "no data", 1: "saturated", 2: "dark area", 3: "cloud shadow",
             4: "vegetation", 5: "bare soil", 6: "water", 7: "unclassified",
             8: "cloud (medium)", 9: "cloud (high)", 10: "thin cirrus", 11: "snow/ice"}
SCL_COLORS = ["#000000", "#ff0000", "#2f2f2f", "#6b4a2b", "#3fa535", "#e8d27a",
              "#1f5fd1", "#8a8a8a", "#c8c8c8", "#ffffff", "#7fd8ff", "#ff7fe8"]

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="e.g. 2024-08-12")
args = parser.parse_args()

cfg = load_config()
keep = cfg["scl_keep"]
dilate = cfg["cloud_dilate_px"]

# ---------- 1. Load one date ----------
item = get_item_for_date(args.date)
print("Scene:", item.id, "| baseline", item.properties.get("s2:processing_baseline"),
      "| tile-wide cloud", item.properties["eo:cloud_cover"], "%")
ds = load_lazy([item], ["B02", "B03", "B04", "B08", "SCL"]).isel(time=0).compute()
dn = np.stack([ds[b].values for b in ["B02", "B03", "B04", "B08"]])
dn = np.nan_to_num(dn, nan=0).astype("uint16")      # NaN -> 0 (no data)
scl = np.nan_to_num(ds.SCL.values, nan=0).astype("uint8")

valid = (dn > 0).all(axis=0) & (scl > 0)
refl = to_reflectance(dn)
refl[:, ~valid] = np.nan
blue, green, red, nir = refl[0], refl[1], refl[2], refl[3]
ndvi = compute_ndvi(nir, red)
nv = valid.sum()

# ---------- 2. SCL composition ----------
print("\nSCL classes (% of valid pixels)")
for v in np.unique(scl[valid]):
    print(f"  {v:2d} {SCL_NAMES[int(v)]:15s} {(valid & (scl == v)).sum() / nv * 100:6.2f}%")

# ---------- 3. Distance to the nearest cloud or shadow ----------
core = np.isin(scl, [3, 8, 9, 10])
if core.sum() == 0:
    raise SystemExit("\nNo cloud or shadow pixels in the AOI on this date. "
                     "Pick a cloudier date, e.g. 2024-08-12 or 2022-06-04.")
dist = ndimage.distance_transform_edt(~core)     # pixels (10 m each) to the nearest core pixel

# ---------- 4. Does contamination extend beyond the SCL cloud? ----------
base = valid & np.isin(scl, [4, 5])
far = base & (dist > 100)
far_blue = np.nanmedian(blue[far]) if far.any() else np.nan
print(f"\nReference: clear pixels more than 100 px (1 km) from any cloud: "
      f"blue median {far_blue:.4f} (n={far.sum():,})")
print("\ndistance (px)    n pixels    blue median   vs far    NDVI median")
bins = [(0, 2), (2, 5), (5, 10), (10, 20), (20, 50), (50, 100)]
bin_x, bin_y = [], []
for lo, hi in bins:
    sel = base & (dist > lo) & (dist <= hi)
    if sel.sum() < 200:
        continue
    b = np.nanmedian(blue[sel])
    bin_x.append(f"{lo}-{hi}")
    bin_y.append(b)
    print(f"  {lo:3d}-{hi:<3d}      {sel.sum():9,d}      {b:8.4f}   {b / far_blue:5.2f}x"
          f"     {np.nanmedian(ndvi[sel]):6.3f}")

# ---------- 5. The judgment-call classes ----------
print("\nClasses 2 and 7 versus normal classes")
print("class             n pixels   within 10 px of cloud   blue median")
for c in (2, 4, 5, 7):
    sel = valid & (scl == c)
    if sel.sum() == 0:
        continue
    print(f"  {c} {SCL_NAMES[c]:14s} {sel.sum():9,d}   {(dist[sel] <= 10).mean() * 100:15.1f}%"
          f"        {np.nanmedian(blue[sel]):.4f}")

# ---------- 6. Final mask and a dilation sweep ----------
scl_ok = np.isin(scl, keep)
print(f"\nPixels retained (% of valid) with SCL keep={keep}:")
for n_px in (0, 2, 5, 10, 20):
    kept = valid & scl_ok & (dist > n_px)
    print(f"  dilate {n_px:2d} px: {kept.sum() / nv * 100:6.2f}%")

good = valid & scl_ok & (dist > dilate)
removed_scl = valid & ~scl_ok
removed_ring = valid & scl_ok & (dist <= dilate)
print(f"\nChosen dilation: {dilate} px")
print(f"  kept                      {good.sum() / nv * 100:6.2f}%")
print(f"  removed by SCL class      {removed_scl.sum() / nv * 100:6.2f}%")
print(f"  removed by dilation ring  {removed_ring.sum() / nv * 100:6.2f}%")

# ---------- 7. Figure ----------
def stretch(a, lo, hi):
    return np.nan_to_num(np.clip((a - lo) / (hi - lo), 0, 1))

rgb = np.dstack([stretch(red, 0, 0.3), stretch(green, 0, 0.3), stretch(blue, 0, 0.3)])
cat = np.zeros(scl.shape, dtype="uint8")          # 0 no data
cat[good] = 1
cat[removed_scl] = 2
cat[removed_ring] = 3
mask_colors = ["#000000", "#2ca02c", "#d62728", "#ff9f1c"]

fig, axes = plt.subplots(2, 2, figsize=(15, 14))
axes[0, 0].imshow(rgb)
axes[0, 0].set_title(f"True color {args.date} (fixed stretch 0-0.3)")
axes[0, 1].imshow(scl, cmap=ListedColormap(SCL_COLORS), vmin=0, vmax=11, interpolation="nearest")
axes[0, 1].set_title("SCL")
present = [int(v) for v in np.unique(scl)]
axes[0, 1].legend(handles=[Patch(color=SCL_COLORS[v], label=f"{v} {SCL_NAMES[v]}") for v in present],
                  loc="lower left", fontsize=8, framealpha=0.9)
axes[1, 0].imshow(cat, cmap=ListedColormap(mask_colors), vmin=0, vmax=3, interpolation="nearest")
axes[1, 0].set_title(f"Mask: kept (green), SCL-removed (red), dilation {dilate}px (orange)")
for ax in (axes[0, 0], axes[0, 1], axes[1, 0]):
    ax.axis("off")
axes[1, 1].plot(bin_x, bin_y, "o-", label="blue median by distance to cloud")
axes[1, 1].axhline(far_blue, color="gray", linestyle="--", label="far from cloud (>100 px)")
axes[1, 1].set_xlabel("distance to nearest cloud/shadow (pixels)")
axes[1, 1].set_ylabel("blue reflectance (clear pixels)")
axes[1, 1].legend()
axes[1, 1].set_title("Is blue elevated near clouds?")

fig.tight_layout()
out_png = ROOT / "outputs" / f"day8_cloud_mask_{args.date}.png"
fig.savefig(out_png, dpi=100)
print("\nSaved figure:", out_png)
plt.show()