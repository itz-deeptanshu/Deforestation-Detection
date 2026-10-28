import numpy as np
import rasterio

from config import ROOT, load_config
from label_utils import build_labels
from scene_io import compute_ndvi

cfg = load_config()
L = build_labels()
with rasterio.open(ROOT / "data" / "composites" / "composite_a.tif") as src:
    comp = src.read().astype("float32")
    comp[comp == -9999.0] = np.nan
ndvi = compute_ndvi(comp[3], comp[2])
ok = np.isfinite(ndvi)
ndvi_forest = ok & (ndvi > cfg["ndvi_forest_threshold"])
conf = ~L["gain"]

R = 8
M = R + 2


def iou_shift(a, b, valid, dr, dc):
    """IoU of a(r, c) with b(r + dr, c + dc) over pixels valid at both positions."""
    H, W = a.shape
    aa = a[M:H - M, M:W - M]
    bb = b[M + dr:H - M + dr, M + dc:W - M + dc]
    vv = valid[M:H - M, M:W - M] & valid[M + dr:H - M + dr, M + dc:W - M + dc]
    return (aa & bb & vv).sum() / max(((aa | bb) & vv).sum(), 1)


pairs = (
    ("Hansen vs WorldCover 2021", L["h_A"], L["w_A"], conf),
    ("Hansen vs NDVI forest", L["h_A"], ndvi_forest, conf & ok),
    ("WorldCover vs NDVI forest", L["w_A"], ndvi_forest, conf & ok),
)
shifts = range(-R, R + 1)
for name, a, b, valid in pairs:
    grid = {(dr, dc): iou_shift(a, b, valid, dr, dc) for dr in shifts for dc in shifts}
    best = max(grid, key=grid.get)
    gain = grid[best] - grid[(0, 0)]
    edge = max(abs(best[0]), abs(best[1])) == R
    print(f"\n{name}")
    print(f"  IoU at (0,0) {grid[(0, 0)]:.3f}; best shift (rows, cols) = {best}, IoU {grid[best]:.3f} "
          f"(gain {gain:+.3f}); best is on the search edge: {edge}")
    print("  IoU along rows at the best column shift  (dr = -8 ... +8):")
    print("   ", " ".join(f"{grid[(dr, best[1])]:.3f}" for dr in shifts))
    print("  IoU along columns at the best row shift  (dc = -8 ... +8):")
    print("   ", " ".join(f"{grid[(best[0], dc)]:.3f}" for dc in shifts))
    print(f"  verdict: interior peak = {not edge}, gain >= 0.03 = {gain >= 0.03}")

print("\nRule fixed in advance: shift Hansen only if (a) Hansen vs WorldCover AND Hansen vs NDVI both show")
print("an interior peak, (b) both gains are >= 0.03, and (c) the two best shifts agree within 1 pixel.")
print("Otherwise labels stay unshifted.")