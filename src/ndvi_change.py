import argparse

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap
from scipy import ndimage

from config import ROOT, load_config
from scene_io import compute_ndvi, load_saved_scene

PIXEL_HA = 0.01
MMU_PIXELS = 50                 # 0.5 ha
KEEP_SCL = [4, 5]               # vegetation, bare soil

parser = argparse.ArgumentParser()
parser.add_argument("--a", default="2022-07-09", help="earlier date")
parser.add_argument("--b", default="2024-07-13", help="later date")
parser.add_argument("--drop", type=float, default=0.25, help="NDVI drop to flag")
args = parser.parse_args()

cfg = load_config()
thr = cfg["ndvi_forest_threshold"]


def stretch(a, lo, hi):
    return np.nan_to_num(np.clip((a - lo) / (hi - lo), 0, 1))


def robust(x):
    """Median and MAD-based sigma (see A3)."""
    med = np.median(x)
    return med, 1.4826 * np.median(np.abs(x - med))


def apply_mmu(mask, min_pixels):
    """Remove 8-connected patches smaller than min_pixels."""
    labels, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        return mask.copy(), 0, 0
    sizes = np.bincount(labels.ravel())
    keep = sizes >= min_pixels
    keep[0] = False                         # label 0 is the background
    return keep[labels], n, int(keep.sum())


# ---------- 1. Load both dates and check the grids match ----------
bands_a, valid_a, scl_a, meta_a = load_saved_scene(args.a)
bands_b, valid_b, scl_b, meta_b = load_saved_scene(args.b)
assert meta_a["transform"] == meta_b["transform"], "Grids differ! Stop and check."
assert valid_a.shape == valid_b.shape, "Shapes differ! Stop and check."
print(f"A = {args.a}   B = {args.b}   (same grid: OK)")

ndvi_a = compute_ndvi(bands_a["B08"], bands_a["B04"])
ndvi_b = compute_ndvi(bands_b["B08"], bands_b["B04"])
dndvi = ndvi_b - ndvi_a

both_valid = valid_a & valid_b & np.isfinite(dndvi)
clear = both_valid & np.isin(scl_a, KEEP_SCL) & np.isin(scl_b, KEEP_SCL)
forest_a = clear & (ndvi_a > thr)

print(f"\nPixels valid in both dates : {both_valid.mean() * 100:6.2f}%")
print(f"Clear in both (SCL 4/5)    : {clear.mean() * 100:6.2f}%")
print(f"Forest at A (NDVI > {thr}) : {forest_a.sum() * PIXEL_HA:,.0f} ha")

# ---------- 2. Global shift and noise ----------
print("\nNDVI change statistics")
print("subset              median   sigma_rob     p1      p5     p95     p99")
for label, sel in [("all clear pixels", clear), ("forest at A", forest_a)]:
    med, sig = robust(dndvi[sel])
    p1, p5, p95, p99 = np.percentile(dndvi[sel], [1, 5, 95, 99])
    print(f"{label:18s} {med:7.3f}   {sig:8.3f}  {p1:7.3f} {p5:7.3f} {p95:7.3f} {p99:7.3f}")

print("\nMedian reflectance change (B - A) over clear pixels")
for name in ["B02", "B03", "B04", "B08"]:
    shift = np.median(bands_b[name][clear] - bands_a[name][clear])
    print(f"  {name}: {shift:+.4f}")

# ---------- 3. Symmetry: decreases vs increases ----------
print("\nSymmetry check (clear pixels)")
print("|dNDVI| >   decrease ha   increase ha   decrease/increase")
for t in (0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
    dec = int((clear & (dndvi < -t)).sum())
    inc = int((clear & (dndvi > t)).sum())
    print(f"  {t:4.2f}   {dec * PIXEL_HA:12,.0f} {inc * PIXEL_HA:13,.0f} {dec / max(inc, 1):14.2f}")

# ---------- 4. Candidate clearings ----------
naive = both_valid & (dndvi < -args.drop)
refined = forest_a & (dndvi < -args.drop) & (ndvi_b <= thr)

naive_mmu, naive_n, naive_kept = apply_mmu(naive, MMU_PIXELS)
refined_mmu, ref_n, ref_kept = apply_mmu(refined, MMU_PIXELS)

print(f"\nFlagging rule: drop > {args.drop}")
print(f"{'':32s}    ha    patches   after MMU (ha, patches)")
print(f"{'NAIVE (any pixel that dropped)':32s} {naive.sum() * PIXEL_HA:8,.0f} {naive_n:8,d}   "
      f"{naive_mmu.sum() * PIXEL_HA:8,.0f}  {naive_kept:6,d}")
print(f"{'REFINED (forest -> non-forest)':32s} {refined.sum() * PIXEL_HA:8,.0f} {ref_n:8,d}   "
      f"{refined_mmu.sum() * PIXEL_HA:8,.0f}  {ref_kept:6,d}")

share = refined_mmu.sum() / max(forest_a.sum(), 1) * 100
print(f"\nRefined flags as a share of forest at A: {share:.2f}%")

# ---------- 5. Save outputs ----------
profile = dict(
    driver="GTiff", height=dndvi.shape[0], width=dndvi.shape[1], count=1,
    crs=meta_a["crs"], transform=meta_a["transform"], compress="deflate",
)
stem = f"change_{args.a}_{args.b}_drop{args.drop}"
flag_arr = np.where(both_valid, refined_mmu.astype("uint8"), 255).astype("uint8")
with rasterio.open(ROOT / "data" / "raw" / f"{stem}_flag.tif", "w",
                   dtype="uint8", nodata=255, **profile) as dst:
    dst.write(flag_arr, 1)
d_arr = np.where(both_valid, dndvi, -9999.0).astype("float32")
with rasterio.open(ROOT / "data" / "raw" / f"{stem}_dndvi.tif", "w",
                   dtype="float32", nodata=-9999.0, **profile) as dst:
    dst.write(d_arr, 1)
print("Saved:", ROOT / "data" / "raw" / f"{stem}_flag.tif")

# ---------- 6. Figure ----------
fc_b = np.dstack([stretch(bands_b["B08"], 0, 0.5),
                  stretch(bands_b["B04"], 0, 0.2),
                  stretch(bands_b["B03"], 0, 0.2)])
overlay = fc_b.copy()
overlay[refined_mmu] = [1.0, 1.0, 0.0]          # flagged pixels in yellow

flag_cmap = ListedColormap(["#e8e8e8", "#d62728"])

fig, axes = plt.subplots(2, 3, figsize=(20, 13))

im0 = axes[0, 0].imshow(np.ma.masked_invalid(ndvi_a), cmap="RdYlGn", vmin=0, vmax=1)
axes[0, 0].set_title(f"NDVI  A = {args.a}")
axes[0, 1].imshow(np.ma.masked_invalid(ndvi_b), cmap="RdYlGn", vmin=0, vmax=1)
axes[0, 1].set_title(f"NDVI  B = {args.b}")
im2 = axes[0, 2].imshow(np.ma.masked_invalid(np.where(both_valid, dndvi, np.nan)),
                        cmap="RdBu", vmin=-0.6, vmax=0.6)
axes[0, 2].set_title("dNDVI = B - A   (red = decrease, blue = increase)")
fig.colorbar(im2, ax=axes[0, 2], shrink=0.7)

axes[1, 0].hist(dndvi[clear], bins=200, range=(-0.8, 0.8), color="gray")
axes[1, 0].set_yscale("log")
axes[1, 0].axvline(-args.drop, color="red", linestyle="--", label=f"-{args.drop}")
axes[1, 0].axvline(args.drop, color="blue", linestyle="--", label=f"+{args.drop}")
axes[1, 0].set_title("dNDVI histogram (log scale)")
axes[1, 0].set_xlabel("dNDVI")
axes[1, 0].legend()

axes[1, 1].imshow(naive_mmu, cmap=flag_cmap, vmin=0, vmax=1, interpolation="nearest")
axes[1, 1].set_title(f"NAIVE flags after MMU: {naive_mmu.sum() * PIXEL_HA:,.0f} ha")
axes[1, 2].imshow(overlay)
axes[1, 2].set_title(f"REFINED flags (yellow) on false color B: {refined_mmu.sum() * PIXEL_HA:,.0f} ha")

for i, ax in enumerate(axes.ravel()):
    if i != 3:
        ax.axis("off")
fig.tight_layout()
out_png = ROOT / "outputs" / f"day6_{stem}.png"
fig.savefig(out_png, dpi=100)
print("Saved figure:", out_png)
plt.show()