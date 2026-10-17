import matplotlib.pyplot as plt
import numpy as np
import rasterio
from skimage.filters import threshold_otsu

from composite_utils import build_composite, masked_reflectance, selected_dates
from config import ROOT, load_config
from scene_io import compute_ndvi

cfg = load_config()
thr = cfg["ndvi_forest_threshold"]
dates = selected_dates("period_a")
REF_DATE = "2022-07-09"


def robust(x):
    med = np.median(x)
    return med, 1.4826 * np.median(np.abs(x - med))


def stretch(a, lo, hi):
    return np.nan_to_num(np.clip((a - lo) / (hi - lo), 0, 1))


# ---------- 1. Load the saved composite and the count map ----------
with rasterio.open(ROOT / "data" / "composites" / "composite_a.tif") as src:
    comp = src.read().astype("float32")
    comp[comp == src.nodata] = np.nan
with rasterio.open(ROOT / "data" / "composites" / "count_a.tif") as src:
    count = src.read(1)
ndvi_c = compute_ndvi(comp[3], comp[2])

# ---------- 2. A single clean date on the same grid ----------
refl_s, good_s = masked_reflectance(REF_DATE)
ndvi_s = compute_ndvi(refl_s[3], refl_s[2])

# ---------- 3. Compare distributions ----------
print("NDVI percentiles          p2     p25  median     p75     p98")
for label, nd in (("composite", ndvi_c), (REF_DATE, ndvi_s)):
    q = np.nanpercentile(nd, [2, 25, 50, 75, 98])
    print(f"  {label:12s}        " + "  ".join(f"{v:6.3f}" for v in q))

print("\nForest share (NDVI above threshold)")
for t in (thr, 0.72):
    fc = np.nanmean(ndvi_c[np.isfinite(ndvi_c)] > t) * 100
    fs = np.nanmean(ndvi_s[np.isfinite(ndvi_s)] > t) * 100
    print(f"  threshold {t:.3f}: composite {fc:5.2f}%   {REF_DATE} {fs:5.2f}%")
vals = ndvi_c[np.isfinite(ndvi_c)]
print(f"  Otsu on the composite: {threshold_otsu(vals):.3f}   (single scene, Day 5: 0.616)")

# ---------- 4. Composite minus single date ----------
both = np.isfinite(ndvi_c) & np.isfinite(ndvi_s)
d = (ndvi_c - ndvi_s)[both]
med, sig = robust(d)
print(f"\nComposite - {REF_DATE} NDVI: median {med:+.3f}, robust sigma {sig:.3f}, "
      f"share |d| > 0.1: {(np.abs(d) > 0.1).mean() * 100:.2f}%")

# ---------- 5. Split-half: two composites from interleaved dates ----------
half_a, half_b = dates[0::2], dates[1::2]
print(f"\nSplit-half test\n  half 1: {half_a}\n  half 2: {half_b}")
c1, n1, _ = build_composite(half_a, 2)
c2, n2, _ = build_composite(half_b, 2)
nd1, nd2 = compute_ndvi(c1[3], c1[2]), compute_ndvi(c2[3], c2[2])
ok = np.isfinite(nd1) & np.isfinite(nd2)
dd = (nd1 - nd2)[ok]
med, sig = robust(dd)
print(f"  pixels with >= 2 looks in both halves: {ok.mean() * 100:.2f}%")
print(f"  NDVI difference: median {med:+.3f}, robust sigma {sig:.3f}, "
      f"share |d| > 0.1: {(np.abs(dd) > 0.1).mean() * 100:.2f}%")
print("  For comparison, single dates 10 days apart (Day 6): median -0.028, sigma 0.032")

# ---------- 6. Figure ----------
def false_color(c):
    return np.dstack([stretch(c[3], 0, 0.5), stretch(c[2], 0, 0.2), stretch(c[1], 0, 0.2)])

fig, axes = plt.subplots(2, 3, figsize=(20, 13))
axes[0, 0].imshow(false_color(comp))
axes[0, 0].set_title(f"Composite 2022 ({len(dates)} dates), false color")
axes[0, 1].imshow(false_color(refl_s))
axes[0, 1].set_title(f"Single scene {REF_DATE}, false color")
im = axes[0, 2].imshow(count, cmap="viridis", vmin=0, vmax=len(dates))
axes[0, 2].set_title("Clear observations per pixel")
fig.colorbar(im, ax=axes[0, 2], shrink=0.7)

im2 = axes[1, 0].imshow(np.ma.masked_invalid(ndvi_c), cmap="RdYlGn", vmin=0, vmax=1)
axes[1, 0].set_title("Composite NDVI")
diff_img = np.where(both, ndvi_c - ndvi_s, np.nan)
im3 = axes[1, 1].imshow(np.ma.masked_invalid(diff_img), cmap="RdBu", vmin=-0.3, vmax=0.3)
axes[1, 1].set_title("Composite NDVI minus single-scene NDVI")
fig.colorbar(im3, ax=axes[1, 1], shrink=0.7)
axes[1, 2].hist(ndvi_s[np.isfinite(ndvi_s)], bins=120, range=(-0.2, 1.0), alpha=0.5,
                label=REF_DATE, color="tan")
axes[1, 2].hist(vals, bins=120, range=(-0.2, 1.0), alpha=0.5, label="composite", color="green")
axes[1, 2].axvline(thr, color="red", linestyle="--", label=f"{thr}")
axes[1, 2].set_title("NDVI histograms")
axes[1, 2].legend()

for ax in (axes[0, 0], axes[0, 1], axes[0, 2], axes[1, 0], axes[1, 1]):
    ax.axis("off")
fig.tight_layout()
out_png = ROOT / "outputs" / "day9_composite_check.png"
fig.savefig(out_png, dpi=100)
print("\nSaved figure:", out_png)
plt.show()