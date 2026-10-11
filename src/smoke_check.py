import argparse

import matplotlib.pyplot as plt
import numpy as np
import rasterio

from config import ROOT
from scene_io import find_scene_path, load_saved_scene

parser = argparse.ArgumentParser()
parser.add_argument("--dates", nargs="+", required=True, help="e.g. 2022-07-09 2024-07-13")
args = parser.parse_args()


def stretch(a, lo, hi):
    return np.nan_to_num(np.clip((a - lo) / (hi - lo), 0, 1))


n = len(args.dates)
fig, axes = plt.subplots(1, n, figsize=(6 * n, 6.5))
axes = np.atleast_1d(axes)

print("date        band     p1   median      p99     (clear pixels, SCL 4 or 5)")
medians = {}
floors = {}
aots = {}

for ax, date in zip(axes, args.dates):
    bands, valid, scl, meta = load_saved_scene(date)
    clear = valid & np.isin(scl, [4, 5])

    for name in ["B02", "B03", "B04", "B08"]:
        p1, med, p99 = np.percentile(bands[name][clear], [1, 50, 99])
        print(f"{date}  {name}  {p1:7.3f}  {med:7.3f}  {p99:7.3f}")
        if name == "B02":
            medians[date], floors[date] = med, p1

    aot_path = str(find_scene_path(date)).replace("_aoi.tif", "_aot.tif")
    title = date
    try:
        with rasterio.open(aot_path) as src:
            aot = src.read(1).astype("float32") / 1000.0
        good = aot[aot > 0]
        if good.size:
            aots[date] = float(np.median(good))
            print(f"{date}  AOT median {aots[date]:.3f}   p95 {np.percentile(good, 95):.3f}")
            title = f"{date}   AOT {aots[date]:.2f}"
    except Exception:
        print(f"{date}  (no AOT file)")

    rgb = np.dstack([stretch(bands["B04"], 0, 0.3),
                     stretch(bands["B03"], 0, 0.3),
                     stretch(bands["B02"], 0, 0.3)])
    ax.imshow(rgb)
    ax.set_title(title)
    ax.axis("off")

ref = args.dates[0]
print(f"\nRelative to {ref}:")
for date in args.dates[1:]:
    line = (f"  {date}: blue median x{medians[date] / medians[ref]:.2f}, "
            f"blue dark floor x{floors[date] / floors[ref]:.2f}")
    if date in aots and ref in aots:
        line += f", AOT x{aots[date] / aots[ref]:.2f}"
    print(line)

fig.suptitle("True color (fixed stretch 0-0.3): same stretch on every date", fontsize=13)
fig.tight_layout()
out_png = ROOT / "outputs" / "day6_smoke_check.png"
fig.savefig(out_png, dpi=100)
print("\nSaved figure:", out_png)
plt.show()