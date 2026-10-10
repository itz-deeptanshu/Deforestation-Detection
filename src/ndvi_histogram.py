import matplotlib.pyplot as plt
import numpy as np
from skimage.filters import threshold_otsu

from config import ROOT
from scene_io import compute_ndvi, load_saved_scene

PIXEL_HA = 0.01          # one 10 m pixel = 100 m2 = 0.01 ha

bands, valid, scl, meta = load_saved_scene()
ndvi = compute_ndvi(bands["B08"], bands["B04"])
ok = valid & np.isfinite(ndvi)
vals = ndvi[ok]
print(f"Valid pixels: {vals.size:,}  ({vals.size * PIXEL_HA:,.0f} ha)")

# 1. Otsu threshold
thr = float(threshold_otsu(vals))
print(f"\nOtsu threshold: {thr:.3f}")

# 2. Sensitivity: how much does forest area move with the threshold?
print("\nthreshold   forest %   forest ha   change vs previous (ha)")
prev = None
for t in np.arange(0.40, 0.91, 0.05):
    ha = float((vals > t).sum()) * PIXEL_HA
    delta = "" if prev is None else f"{ha - prev:+,.0f}"
    print(f"   {t:.2f}     {ha / (vals.size * PIXEL_HA) * 100:6.1f}   {ha:10,.0f}   {delta:>10}")
    prev = ha

# 3. Split pixels into two groups using the Otsu threshold
high = ok & (ndvi > thr)       # "forest-like"
low = ok & (ndvi <= thr)       # "non-forest-like"
print(f"\nForest-like : {high.sum() * PIXEL_HA:,.0f} ha ({high.sum() / ok.sum() * 100:.1f}%)")
print(f"Other       : {low.sum() * PIXEL_HA:,.0f} ha ({low.sum() / ok.sum() * 100:.1f}%)")

# 4. How different are the two groups in each band? (d-prime)
print("\nband   median(high)  median(low)   d-prime")
for name in ["B02", "B03", "B04", "B08"]:
    a, b = bands[name][high], bands[name][low]
    d = abs(a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2)
    print(f"{name}      {np.median(a):7.3f}      {np.median(b):7.3f}     {d:6.2f}")
print("(B04 and B08 are biased: NDVI is built from them. B02 and B03 are independent evidence.)")

# 5. Plots
fig, axes = plt.subplots(1, 5, figsize=(21, 4))

axes[0].hist(vals, bins=120, range=(-0.2, 1.0), color="gray")
axes[0].axvline(thr, color="red", linestyle="--", label=f"Otsu {thr:.2f}")
axes[0].set_title("NDVI histogram")
axes[0].set_xlabel("NDVI")
axes[0].legend()

for ax, name in zip(axes[1:], ["B02", "B03", "B04", "B08"]):
    ax.hist(bands[name][high], bins=100, range=(0, 0.5), density=True,
            alpha=0.6, color="green", label="NDVI > thr")
    ax.hist(bands[name][low], bins=100, range=(0, 0.5), density=True,
            alpha=0.6, color="tan", label="NDVI <= thr")
    ax.set_title(f"{name} reflectance")
    ax.set_xlabel("reflectance")
    ax.legend()

fig.tight_layout()
out_png = ROOT / "outputs" / "day5_histograms.png"
fig.savefig(out_png, dpi=110)
print("\nSaved figure:", out_png)
plt.show()