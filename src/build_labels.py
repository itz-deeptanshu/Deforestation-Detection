import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap
from scipy import ndimage

from config import ROOT, load_config
from label_utils import IGNORE, OUT, build_labels
from stack_utils import master_geobox

cfg = load_config()
gb = master_geobox()
PIXEL_HA = 0.01
ha = lambda m: f"{m.sum() * PIXEL_HA:>9,.0f}"

L = build_labels()
A, B, C = L["A"], L["B"], L["change"]

# ---------- 1. Structural checks ----------
for name, arr in (("A", A), ("B", B), ("change", C)):
    assert set(np.unique(arr).tolist()) <= {0, 1, IGNORE}, f"label_{name} has unexpected values"
n_bad = int(((A == 0) & (B == 1)).sum())
assert n_bad == 0, f"{n_bad} pixels are non-forest at A but forest at B (impossible)"
strict = L["base"] & (L["ly"] == 23) & (A == 1)
assert np.array_equal(C == 1, strict), "clearing positives are not exactly 'loss year 2023 on label-A forest'"
print("Checks passed: values are 0/1/255, no non-forest(A) -> forest(B), positives = loss code 2023.")

# ---------- 2. Composition ----------
total = A.size * PIXEL_HA
print(f"\nGrid {A.shape}, {total:,.0f} ha")
print(f"Hansen forest end-2021 (check vs Day 11: 12,617 ha): {ha(L['h_A'])} ha")
print("\nlabel   forest ha   non-forest ha   ignore ha   ignore %")
for name, arr in (("A (2022)", A), ("B (2024)", B)):
    print(f"{name}  {ha(arr == 1)}   {ha(arr == 0)}      {ha(arr == IGNORE)}    "
          f"{(arr == IGNORE).mean() * 100:6.1f}")

names = {0: "labelled", 1: "Hansen gain / no-data", 2: "ambiguous loss year",
         3: "Hansen forest, WorldCover not", 4: "WorldCover tree, Hansen not"}
print("\nWhy pixels are ignored (ha)")
print("reason                           label A    label B")
for k in range(1, 5):
    print(f"{names[k]:30s} {ha(L['reason_A'] == k)}  {ha(L['reason_B'] == k)}")

# ---------- 3. Change label ----------
stable = C == 0
clear = C == 1
print(f"\nChange label: stable forest {ha(stable)} ha, new clearing {ha(clear)} ha")
print(f"  Hansen loss 2023 on year-2000 forest (Day 11): 186 ha. Positives here: {clear.sum() * PIXEL_HA:,.0f} ha")
lab_c, n = ndimage.label(clear, structure=np.ones((3, 3)))
if n:
    sizes = np.bincount(lab_c.ravel())[1:] * PIXEL_HA
    print(f"  clearing patches: {n}, median {np.median(sizes):.2f} ha, largest {sizes.max():.1f} ha, "
          f"share of area in patches >= 0.5 ha: {sizes[sizes >= 0.5].sum() / sizes.sum() * 100:.0f}%")
else:
    print("  no clearing patches found")
print("  Only clearing of old forest that BOTH sources call forest is included (regrowth is excluded).")

# ---------- 4. Save ----------
profile = dict(driver="GTiff", height=A.shape[0], width=A.shape[1], count=1, dtype="uint8",
               crs=f"EPSG:{cfg['utm_epsg']}", transform=gb.affine, nodata=IGNORE,
               compress="deflate", tiled=True, blockxsize=256, blockysize=256)
rules = {
    "A": "forest = Hansen(canopy>=30, no loss through 2021) AND WorldCover2021 tree; ignore: gain, loss 2022, disagreement",
    "B": "forest = Hansen(canopy>=30, no loss through 2023) AND WorldCover2021 tree minus Hansen loss 22-23; ignore: gain, loss 2024, disagreement",
    "change": "1 = forest at A and non-forest at B (loss 2023); 0 = forest at both; 255 otherwise",
}
for name, arr in (("A", A), ("B", B), ("change", C)):
    with rasterio.open(OUT / f"label_{name}.tif", "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(rule=rules[name], hansen_version=cfg["hansen_version"],
                        canopy_min=str(cfg["forest_canopy_min"]), values="1 forest, 0 non-forest, 255 ignore")
print("\nSaved label_A.tif, label_B.tif, label_change.tif to", OUT)

# ---------- 5. Figure ----------
def three(arr, colors):
    return np.where(arr == IGNORE, 2, arr), ListedColormap(colors)

fig, ax = plt.subplots(2, 3, figsize=(20, 13))
for a, arr, title in ((ax[0, 0], A, "label A (2022)"), (ax[0, 1], B, "label B (2024)")):
    img, cm = three(arr, ["#e8d9a8", "#1f7a2e", "#8a8a8a"])
    a.imshow(img, cmap=cm, vmin=0, vmax=2, interpolation="nearest")
    a.set_title(f"{title}: forest green, non-forest tan, ignore grey")
img, cm = three(C, ["#1f7a2e", "#d62728", "#e8e8e8"])
ax[0, 2].imshow(img, cmap=cm, vmin=0, vmax=2, interpolation="nearest")
ax[0, 2].set_title("change: stable forest green, new clearing red, ignore light")
rc = ListedColormap(["#f3efe0", "#9467bd", "#8c564b", "#ff8c00", "#2a6fdb"])
for a, key, title in ((ax[1, 0], "reason_A", "ignore reasons A"), (ax[1, 1], "reason_B", "ignore reasons B")):
    a.imshow(L[key], cmap=rc, vmin=0, vmax=4, interpolation="nearest")
    a.set_title(title + ": gain (purple), ambiguous year (brown),\nHansen only (orange), WorldCover only (blue)")
cats = ["forest", "non-forest", "ignore"]
vals = [[(arr == v).sum() * PIXEL_HA for v in (1, 0, IGNORE)] for arr in (A, B)]
x = np.arange(3)
ax[1, 2].bar(x - 0.2, vals[0], 0.4, label="A (2022)")
ax[1, 2].bar(x + 0.2, vals[1], 0.4, label="B (2024)")
ax[1, 2].set_xticks(x)
ax[1, 2].set_xticklabels(cats)
ax[1, 2].set_ylabel("ha")
ax[1, 2].legend()
for i, a in enumerate(ax.ravel()):
    if i != 5:
        a.axis("off")
fig.tight_layout()
out_png = ROOT / "outputs" / "day12_labels.png"
fig.savefig(out_png, dpi=100)
print("Saved figure:", out_png)
plt.show()