import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage

from composite_utils import BANDS, build_composite, selected_dates
from config import ROOT, load_config
from scene_io import compute_ndvi

cfg = load_config()
thr = cfg["ndvi_forest_threshold"]
PIXEL_HA = 0.01
DROP = 0.25          # same as Day 6; NOT tuned here
MMU = 50             # 0.5 ha


def load(name):
    with rasterio.open(ROOT / "data" / "composites" / f"{name}.tif") as src:
        a = src.read().astype("float32")
        a[a == -9999.0] = np.nan
        return a


def robust(x):
    med = np.median(x)
    return med, 1.4826 * np.median(np.abs(x - med))


def stretch(a, lo, hi):
    return np.nan_to_num(np.clip((a - lo) / (hi - lo), 0, 1))


ca, cb = load("composite_a"), load("composite_b")
count_b = load("count_b")[0]
na, nb = compute_ndvi(ca[3], ca[2]), compute_ndvi(cb[3], cb[2])
both = np.isfinite(na) & np.isfinite(nb)
d = nb - na
print(f"Pixels valid in both composites: {both.mean() * 100:.2f}%")

# ---------- 1. Overall shift and noise ----------
forest_a = both & (na > thr)
print(f"Forest at A (composite, NDVI > {thr}): {forest_a.sum() * PIXEL_HA:,.0f} ha")
print("\nNDVI change (2024 - 2022 composites)")
print("subset                  median   sigma_rob       p1      p5     p95     p99")
for label, sel in (("all valid pixels", both), ("forest at A", forest_a)):
    med, sig = robust(d[sel])
    q = np.percentile(d[sel], [1, 5, 95, 99])
    print(f"{label:22s} {med:8.3f}   {sig:8.3f}  {q[0]:7.3f} {q[1]:7.3f} {q[2]:7.3f} {q[3]:7.3f}")
print("Day 6 single dates:   all -0.066 / 0.074     forest at A -0.035 / 0.044")
print("Day 6 null (10 days): all -0.028 / 0.032     forest at A -0.008 / 0.023")

print("\nMedian reflectance change (2024 - 2022 composite), valid pixels")
for k, nm in enumerate(BANDS):
    print(f"  {nm}: {np.median((cb[k] - ca[k])[both]):+.4f}")
print("Day 6 single dates: B02 +0.0108  B03 +0.0088  B04 +0.0188  B08 +0.0074")

# ---------- 2. Where is the shift? (descriptive) ----------
fb = both & (nb > thr)
classes = {
    "forest in both years": both & (na > thr) & (nb > thr),
    "non-forest in both": both & (na <= thr) & (nb <= thr),
    "forest -> non-forest": both & (na > thr) & (nb <= thr),
    "non-forest -> forest": both & (na <= thr) & (nb > thr),
}
print("\nClass (by NDVI, descriptive only)    ha      median dNDVI   median dRed")
for label, sel in classes.items():
    if sel.sum() == 0:
        continue
    print(f"  {label:22s} {sel.sum() * PIXEL_HA:9,.0f}   {np.median(d[sel]):10.3f}   "
          f"{np.median((cb[2] - ca[2])[sel]):10.4f}")

# ---------- 3. Symmetry and the Day 6 rule on composites ----------
print("\n|dNDVI| >   decrease ha   increase ha   ratio")
for t in (0.15, 0.20, 0.25, 0.30, 0.40):
    dec = int((both & (d < -t)).sum())
    inc = int((both & (d > t)).sum())
    print(f"  {t:4.2f}   {dec * PIXEL_HA:11,.0f} {inc * PIXEL_HA:12,.0f} {dec / max(inc, 1):8.1f}")
print("Day 6 single dates at 0.25: 2,019 ha vs 75 ha")

refined = forest_a & (d < -DROP) & (nb <= thr)
labels, n = ndimage.label(refined, structure=np.ones((3, 3)))
sizes = np.bincount(labels.ravel())
keep = sizes >= MMU
keep[0] = False
refined_mmu = keep[labels]
print(f"\nRefined flags (forest -> non-forest, drop > {DROP}), composites:")
print(f"  before MMU {refined.sum() * PIXEL_HA:,.0f} ha ({n:,} patches)   "
      f"after MMU {refined_mmu.sum() * PIXEL_HA:,.0f} ha ({int(keep.sum()):,} patches)")
print(f"  share of forest at A: {refined_mmu.sum() / max(forest_a.sum(), 1) * 100:.2f}%")
print("  Day 6 single dates: 1,327 ha before MMU (10,005 patches), 886 ha after (369 patches)")
print("  This is still an UPPER BOUND, not a deforestation estimate.")
low = refined_mmu & (count_b < 5)
print(f"  flagged pixels where 2024 had fewer than 5 looks: {low.sum() / max(refined_mmu.sum(), 1) * 100:.1f}%")

# ---------- 4. 2024 split-half (null experiment for composites) ----------
dates_b = selected_dates("period_b")
h1, h2 = dates_b[0::2], dates_b[1::2]
print(f"\n2024 split-half\n  half 1: {h1}\n  half 2: {h2}")
c1, _, _ = build_composite(h1, 2)
c2, _, _ = build_composite(h2, 2)
n1, n2 = compute_ndvi(c1[3], c1[2]), compute_ndvi(c2[3], c2[2])
ok = np.isfinite(n1) & np.isfinite(n2)
med, sig = robust((n1 - n2)[ok])
print(f"  NDVI difference between halves: median {med:+.3f}, robust sigma {sig:.3f}")
print("  Compare with your 2022 split-half from Day 9.")
print("  Cross-year sigma above should be well above the within-year sigma if the change is real.")

# ---------- 5. Figure ----------
def fc(c):
    return np.dstack([stretch(c[3], 0, 0.5), stretch(c[2], 0, 0.2), stretch(c[1], 0, 0.2)])

fig, axes = plt.subplots(2, 3, figsize=(20, 13))
axes[0, 0].imshow(fc(ca)); axes[0, 0].set_title("Composite 2022, false color")
axes[0, 1].imshow(fc(cb)); axes[0, 1].set_title("Composite 2024, false color")
im = axes[0, 2].imshow(np.ma.masked_invalid(np.where(both, d, np.nan)), cmap="RdBu", vmin=-0.4, vmax=0.4)
axes[0, 2].set_title("dNDVI composite (2024 - 2022)")
fig.colorbar(im, ax=axes[0, 2], shrink=0.7)
im2 = axes[1, 0].imshow(count_b, cmap="viridis", vmin=0, vmax=len(dates_b))
axes[1, 0].set_title("2024 clear observations")
fig.colorbar(im2, ax=axes[1, 0], shrink=0.7)
axes[1, 1].hist(d[both], bins=200, range=(-0.8, 0.8), color="gray")
axes[1, 1].set_yscale("log")
axes[1, 1].axvline(-DROP, color="red", linestyle="--", label=f"-{DROP}")
axes[1, 1].set_title("dNDVI histogram (log)")
axes[1, 1].legend()
ov = fc(cb).copy()
ov[refined_mmu] = [1.0, 1.0, 0.0]
axes[1, 2].imshow(ov)
axes[1, 2].set_title(f"Refined flags (yellow): {refined_mmu.sum() * PIXEL_HA:,.0f} ha")
for i, ax in enumerate(axes.ravel()):
    if i != 4:
        ax.axis("off")
fig.tight_layout()
out_png = ROOT / "outputs" / "day10_composite_compare.png"
fig.savefig(out_png, dpi=100)
print("\nSaved figure:", out_png)
plt.show()