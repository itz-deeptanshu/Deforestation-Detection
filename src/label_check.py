import numpy as np
import rasterio

from config import ROOT, load_config
from label_utils import IGNORE, OUT, build_labels
from scene_io import compute_ndvi
from stack_utils import master_geobox

cfg = load_config()
gb = master_geobox()
problems = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label} {detail}")
    if not ok:
        problems.append(label)


# ---------- 1. Files are on the master grid ----------
print("--- 1. Metadata ---")
for n in ("A", "B", "change"):
    with rasterio.open(OUT / f"label_{n}.tif") as src:
        check(src.transform == gb.affine and (src.height, src.width) == tuple(gb.shape),
              f"label_{n} on the master grid", f"origin ({src.transform.c:.0f}, {src.transform.f:.0f})")
        check(src.dtypes[0] == "uint8" and src.nodata == IGNORE, f"label_{n} dtype/nodata")
        check("rule" in src.tags(), f"label_{n} carries its rule in the tags")
with rasterio.open(ROOT / "data" / "composites" / "composite_a.tif") as src:
    comp = src.read().astype("float32")
    comp[comp == -9999.0] = np.nan
    check(src.transform == gb.affine, "composite_a and labels share a transform")

L = build_labels()
A = L["A"]
ndvi = compute_ndvi(comp[3], comp[2])
ok = np.isfinite(ndvi)
ndvi_forest = ok & (ndvi > cfg["ndvi_forest_threshold"])

# ---------- 2. Registration (integer shifts of +-3 px) ----------
print("\n--- 2. Registration against composite-A NDVI forest ---")


def iou_at(src_mask, conf, dr, dc, m=5):
    """Compare label(r, c) with NDVI forest at (r+dr, c+dc), inside confident, valid pixels."""
    H, W = src_mask.shape
    a = src_mask[m:H - m, m:W - m]
    c = conf[m:H - m, m:W - m]
    b = ndvi_forest[m + dr:H - m + dr, m + dc:W - m + dc]
    v = ok[m + dr:H - m + dr, m + dc:W - m + dc]
    use = c & v
    return (a & b & use).sum() / max(((a | b) & use).sum(), 1)


tests = (("Hansen end-2021", L["h_A"], ~L["gain"]),
         ("WorldCover 2021", L["w_A"], ~L["gain"]),
         ("label A (agreement)", A == 1, A != IGNORE))
shifts = range(-3, 4)
for name, mask, conf in tests:
    grid = {(dr, dc): iou_at(mask, conf, dr, dc) for dr in shifts for dc in shifts}
    best = max(grid, key=grid.get)
    print(f"\n{name}: IoU at (0,0) = {grid[(0, 0)]:.3f}; best shift (rows, cols) = {best} "
          f"with IoU {grid[best]:.3f}")
    print("   rows\\cols " + " ".join(f"{dc:+d}".rjust(6) for dc in range(-2, 3)))
    for dr in range(-2, 3):
        print(f"   {dr:+d}       " + " ".join(f"{grid[(dr, dc)]:6.3f}" for dc in range(-2, 3)))
print("\nReading: a best shift of (dr, dc) means the imagery matches the labels best when read dr rows south")
print("and dc columns east. One pixel = 10 m. Nothing is shifted automatically.")

# ---------- 3. Separability with independent labels ----------
print("\n--- 3. Composite-A values by label class (labels are independent of our bands) ---")
fo = (A == 1) & ok
nf = (A == 0) & ok
print(f"forest pixels {fo.sum() * 0.01:,.0f} ha, non-forest {nf.sum() * 0.01:,.0f} ha")
print("quantity    forest median [p5-p95]        non-forest median [p5-p95]     d-prime")
feat = {"B02": comp[0], "B03": comp[1], "B04": comp[2], "B08": comp[3], "NDVI": ndvi}
for k, v in feat.items():
    f, n = v[fo], v[nf]
    q1, q0 = np.percentile(f, [5, 50, 95]), np.percentile(n, [5, 50, 95])
    d = abs(f.mean() - n.mean()) / np.sqrt((f.var() + n.var()) / 2)
    print(f"{k:5s}       {q1[1]:6.3f} [{q1[0]:6.3f}-{q1[2]:6.3f}]      "
          f"{q0[1]:6.3f} [{q0[0]:6.3f}-{q0[2]:6.3f}]     {d:6.2f}")
print("Day 5 d-prime (circular, groups defined by NDVI): B02 2.90, B03 2.29, B04 3.17, B08 0.65")

# ---------- 4. The NDVI baseline on confident pixels ----------
print("\n--- 4. NDVI forest (0.616) on confident label-A pixels (descriptive, no tuning) ---")
conf = (A != IGNORE) & ok
a, r = ndvi_forest[conf], (A == 1)[conf]
tp, fp, fn = (a & r).sum(), (a & ~r).sum(), (~a & r).sum()
print(f"precision {tp / (tp + fp):.3f}, recall {tp / (tp + fn):.3f}, IoU {tp / (tp + fp + fn):.3f}  "
      f"(Day 11 vs Hansen alone: 0.42 / 0.76 / 0.374)")
print(f"NDVI-forest pixels falling on ignored label pixels: "
      f"{(ndvi_forest & (A == IGNORE)).sum() * 0.01:,.0f} ha of {ndvi_forest.sum() * 0.01:,.0f} ha")

print("\nALL CHECKS PASSED" if not problems else f"\n{len(problems)} problem(s): {problems}")