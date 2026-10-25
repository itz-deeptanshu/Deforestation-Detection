import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap, to_rgb
from rasterio.warp import Resampling, reproject

from config import ROOT, load_config
from scene_io import compute_ndvi
from stack_utils import master_geobox

cfg = load_config()
gb = master_geobox()
RAW = ROOT / "data" / "labels" / "raw"
EPSG = f"EPSG:{cfg['utm_epsg']}"
PIXEL_HA = 0.01
T = cfg["forest_canopy_min"]
A = lambda ha: f"{ha:,.0f}"


def on_master(name):
    """Read a label raster onto the master grid with nearest neighbor (categorical-safe)."""
    with rasterio.open(RAW / f"{name}.tif") as src:
        dst = np.zeros(tuple(gb.shape), dtype=src.dtypes[0])
        reproject(source=rasterio.band(src, 1), destination=dst,
                  dst_transform=gb.affine, dst_crs=EPSG, resampling=Resampling.nearest)
    return dst


tc = on_master("hansen_treecover2000")
ly = on_master("hansen_lossyear")
gain = on_master("hansen_gain")
dm = on_master("hansen_datamask")
wc20, wc21 = on_master("worldcover_2020"), on_master("worldcover_2021")
land = dm == 1
total = tc.size
print(f"Grid {tc.shape}: {total * PIXEL_HA:,.0f} ha")


def hansen_forest(end_year, thr=T):
    """Forest at the END of end_year: canopy >= thr in 2000 and no loss up to that year."""
    lost = (ly >= 1) & (ly <= end_year - 2000)
    return land & (tc >= thr) & ~lost


def crosstab(a, b, na="A", nb="B"):
    both, ao, bo = (a & b).sum(), (a & ~b).sum(), (~a & b).sum()
    neither = (~a & ~b).sum()
    iou = both / max(both + ao + bo, 1)
    print(f"  both {A(both * PIXEL_HA)} ha | only {na} {A(ao * PIXEL_HA)} | only {nb} {A(bo * PIXEL_HA)} "
          f"| neither {A(neither * PIXEL_HA)} | IoU {iou:.3f}")
    return iou


# ---------- 1. What is in the window ----------
print("\n--- 1. Hansen mask and WorldCover composition ---")
print("Hansen datamask: " + ", ".join(f"{n} {(dm == v).mean() * 100:.1f}%"
      for v, n in ((0, 'nodata'), (1, 'land'), (2, 'water'))))
print(f"Hansen canopy in 2000 >= {T}%: {A((land & (tc >= T)).sum() * PIXEL_HA)} ha "
      f"({(land & (tc >= T)).mean() * 100:.1f}% of the AOI)")
names = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up",
         60: "bare/sparse", 80: "water", 90: "herbaceous wetland", 95: "mangroves", 100: "moss/lichen"}
for yr, wc in (("2020", wc20), ("2021", wc21)):
    print(f"WorldCover {yr}: " + ", ".join(
        f"{names.get(int(v), v)} {c / total * 100:.1f}%"
        for v, c in zip(*np.unique(wc, return_counts=True)) if c / total > 0.001))

# ---------- 2. Two independent sources, same year (2020) ----------
print("\n--- 2. Hansen forest (end of 2020) vs WorldCover 2020 tree cover ---")
print(f"Canopy threshold {T}% (decided in advance):")
crosstab(hansen_forest(2020), wc20 == 10, "Hansen", "WorldCover")
print("\nSensitivity to the canopy threshold (a measurement, NOT a tuning step):")
print("  canopy >=   Hansen ha   IoU vs WorldCover 2020")
for t in (10, 20, 30, 40, 50, 60, 70):
    h = hansen_forest(2020, t)
    i = (h & (wc20 == 10)).sum() / max((h | (wc20 == 10)).sum(), 1)
    print(f"    {t:3d}%    {A(h.sum() * PIXEL_HA):>9}      {i:.3f}")

# ---------- 3. Loss and gain by year ----------
print("\n--- 3. Hansen loss by year (pixels with canopy >= threshold in 2000) ---")
base = land & (tc >= T)
print(f"Forest in 2000 within AOI: {A(base.sum() * PIXEL_HA)} ha")
print("year   loss ha   cumulative % of 2000 forest")
cum = 0
for code in range(1, int(ly.max()) + 1):
    ha = (base & (ly == code)).sum() * PIXEL_HA
    cum += ha
    print(f"{2000 + code}  {A(ha):>8}   {cum / (base.sum() * PIXEL_HA) * 100:6.1f}%")
print(f"Gain (2000-2012) pixels: {A((gain == 1).sum() * PIXEL_HA)} ha "
      f"(of which {A(((gain == 1) & base).sum() * PIXEL_HA)} ha also forest in 2000)")

# ---------- 4. Timing conventions for our composites ----------
print("\n--- 4. Labels for composite dates (A = Jun-Jul 2022, B = Jun-Jul 2024) ---")
forest_a = hansen_forest(2021)
print(f"Forest at A (no loss through 2021): {A(forest_a.sum() * PIXEL_HA)} ha")
for code, label in ((22, "2022 (ambiguous)"), (23, "2023 (between composites)"),
                    (24, "2024 (ambiguous)"), (25, "2025 (after B)")):
    if code <= ly.max():
        print(f"  loss {label}: {A((base & (ly == code)).sum() * PIXEL_HA)} ha")
print("Day 6 upper bound from single-date NDVI differencing: 886 ha (drop 0.25).")

# ---------- 5. WorldCover 2020 -> 2021 ----------
print("\n--- 5. WorldCover tree 2020 -> 2021 (versions differ; not real change) ---")
crosstab(wc20 == 10, wc21 == 10, "tree2020", "tree2021")

# ---------- 6. Our NDVI forest vs the labels (descriptive) ----------
print("\n--- 6. Composite-A NDVI forest vs labels (descriptive, no tuning) ---")
comp_path = ROOT / "data" / "composites" / "composite_a.tif"
ndvi_forest = None
if comp_path.exists():
    with rasterio.open(comp_path) as src:
        c = src.read().astype("float32")
        c[c == -9999.0] = np.nan
    nd = compute_ndvi(c[3], c[2])
    ok = np.isfinite(nd)
    ndvi_forest = ok & (nd > cfg["ndvi_forest_threshold"])
    lab = forest_a & (gain != 1)
    print(f"Valid composite pixels: {ok.mean() * 100:.2f}%")
    for name, ref in (("Hansen forest end-2021", lab), ("WorldCover 2021 tree", wc21 == 10)):
        a, r = ndvi_forest[ok], ref[ok]
        prec = (a & r).sum() / max(a.sum(), 1)
        rec = (a & r).sum() / max(r.sum(), 1)
        print(f"  vs {name}: NDVI-forest {A(a.sum() * PIXEL_HA)} ha, label {A(r.sum() * PIXEL_HA)} ha, "
              f"precision {prec:.2f}, recall {rec:.2f}, IoU {(a & r).sum() / max((a | r).sum(), 1):.3f}")
    print("  Labels are noisy, so this is not an accuracy. It is the first NDVI-independent comparison.")
else:
    print("composite_a.tif not found; skipped.")

# ---------- 7. Figure ----------
WC = {10: "#006400", 20: "#ffbb22", 30: "#ffff4c", 40: "#f096ff", 50: "#fa0000",
      60: "#b4b4b4", 70: "#f0f0f0", 80: "#0064c8", 90: "#0096a0", 95: "#00cf75", 100: "#fae6a0"}
rgb = np.ones(wc21.shape + (3,))
for k, col in WC.items():
    rgb[wc21 == k] = to_rgb(col)
agree = np.zeros(tc.shape, dtype="uint8")
h21 = hansen_forest(2021)
agree[h21 & (wc21 == 10)] = 1
agree[h21 & (wc21 != 10)] = 2
agree[~h21 & (wc21 == 10)] = 3

fig, ax = plt.subplots(2, 3, figsize=(20, 13))
ax[0, 0].imshow(np.where(land, tc, np.nan), cmap="Greens", vmin=0, vmax=100)
ax[0, 0].set_title("Hansen canopy cover 2000 (%)")
ly_show = np.ma.masked_where(ly == 0, ly)
im = ax[0, 1].imshow(ly_show, cmap="plasma", vmin=1, vmax=int(ly.max()), interpolation="nearest")
ax[0, 1].set_title("Hansen loss year (code 1 = 2001)")
fig.colorbar(im, ax=ax[0, 1], shrink=0.7)
ax[0, 2].imshow(rgb)
ax[0, 2].set_title("WorldCover 2021 (dark green = tree cover)")
ax[1, 0].imshow(agree, cmap=ListedColormap(["#e8d9a8", "#1f7a2e", "#ff8c00", "#2a6fdb"]),
                vmin=0, vmax=3, interpolation="nearest")
ax[1, 0].set_title("Hansen end-2021 vs WorldCover 2021: neither (tan), both (green),\nHansen only (orange), WorldCover only (blue)")
if ndvi_forest is not None:
    ax[1, 1].imshow(ndvi_forest, cmap=ListedColormap(["#e8d9a8", "#1f7a2e"]), interpolation="nearest")
    ax[1, 1].set_title("Composite-A NDVI forest (0.616)")
years = np.arange(1, int(ly.max()) + 1)
ax[1, 2].bar(2000 + years, [(base & (ly == y)).sum() * PIXEL_HA for y in years], color="firebrick")
ax[1, 2].set_title("Hansen loss per year (ha)")
for i, a_ in enumerate(ax.ravel()):
    if i != 5:
        a_.axis("off")
fig.tight_layout()
out_png = ROOT / "outputs" / "day11_labels.png"
fig.savefig(out_png, dpi=100)
print("\nSaved figure:", out_png)
plt.show()