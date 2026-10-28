import numpy as np
import rasterio

from config import ROOT
from label_utils import build_labels
from scene_io import compute_ndvi

R = 8                 # search range in pixels
EXPECT = (4, 3)       # best shift from the Day 12 shift test
GAIN_MIN = 0.10       # criterion, fixed before running: absolute rise in share of strong-drop pixels
DROP = -0.25          # a "strong drop" in composite NDVI


def load(name):
    with rasterio.open(ROOT / "data" / "composites" / f"{name}.tif") as src:
        a = src.read().astype("float32")
        a[a == -9999.0] = np.nan
    return a


ca, cb = load("composite_a"), load("composite_b")
d = compute_ndvi(cb[3], cb[2]) - compute_ndvi(ca[3], ca[2])      # NDVI change 2022 -> 2024
H, W = d.shape

L = build_labels()
masks = {
    "loss 2023 (between composites)": L["base"] & (L["ly"] == 23),
    "CONTROL loss 2018 (cleared long before A)": L["base"] & (L["ly"] == 18),
}


def profile(mask):
    rows, cols = np.nonzero(mask)
    out = {}
    for dr in range(-R, R + 1):
        for dc in range(-R, R + 1):
            rr, cc = rows + dr, cols + dc
            inside = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
            v = d[rr[inside], cc[inside]]
            v = v[np.isfinite(v)]
            out[(dr, dc)] = (float((v < DROP).mean()), float(np.median(v)), int(v.size))
    return out


results = {}
for name, m in masks.items():
    p = profile(m)
    results[name] = p
    best = max(p, key=lambda k: p[k][0])
    f0, f_best = p[(0, 0)][0], p[best][0]
    print(f"\n{name}: {int(m.sum()):,} pixels ({m.sum() * 0.01:,.0f} ha)")
    print(f"  at (0,0):   share with dNDVI < {DROP}: {f0:.3f}, median dNDVI {p[(0, 0)][1]:+.3f}")
    print(f"  at best {best}: share {f_best:.3f}, median {p[best][1]:+.3f}  (gain {f_best - f0:+.3f})")
    spread = max(v[0] for v in p.values()) - min(v[0] for v in p.values())
    print(f"  spread of the share across all shifts: {spread:.3f}")
    print("  share along rows at the best column shift (dr = -8 ... +8):")
    print("   ", " ".join(f"{p[(dr, best[1])][0]:.2f}" for dr in range(-R, R + 1)))
    print("  share along columns at the best row shift (dc = -8 ... +8):")
    print("   ", " ".join(f"{p[(best[0], dc)][0]:.2f}" for dc in range(-R, R + 1)))

name = "loss 2023 (between composites)"
p = results[name]
best = max(p, key=lambda k: p[k][0])
gain = p[best][0] - p[(0, 0)][0]
interior = max(abs(best[0]), abs(best[1])) < R
near = abs(best[0] - EXPECT[0]) <= 1 and abs(best[1] - EXPECT[1]) <= 1
print("\nRule fixed in advance (all three must hold to shift Hansen):")
print(f"  [{'PASS' if interior else 'FAIL'}] interior peak (best {best})")
print(f"  [{'PASS' if gain >= GAIN_MIN else 'FAIL'}] gain >= {GAIN_MIN} (gain {gain:+.3f})")
print(f"  [{'PASS' if near else 'FAIL'}] best within 1 px of {EXPECT}")
ctrl = results["CONTROL loss 2018 (cleared long before A)"]
cspread = max(v[0] for v in ctrl.values()) - min(v[0] for v in ctrl.values())
print(f"  control spread {cspread:.3f} (should be small; the 2023 response should stand well above it)")
print("ALL THREE PASS: apply the shift." if interior and gain >= GAIN_MIN and near
      else "NOT ALL PASS: labels stay unshifted.")