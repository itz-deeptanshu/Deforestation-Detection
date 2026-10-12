import time
from collections import Counter

from config import load_config
from stack_utils import load_lazy, master_geobox, search_dates

cfg = load_config()

gb = master_geobox()
print("Master grid shape (rows, cols):", tuple(gb.shape))
print("Master grid affine            :", gb.affine)

# 1. Search and deduplicate each period
all_items = []
for name in ("period_a", "period_b"):
    p = cfg[name]
    raw, unique = search_dates(p["start"], p["end"], cfg["max_scene_cloud_pct"])
    mix = Counter(it.properties.get("s2:processing_baseline") for it in unique)
    print(f"\n{name}: {len(raw)} items -> {len(unique)} unique dates "
          f"({len(raw) - len(unique)} duplicates removed)")
    print("  baselines kept:", dict(mix))
    all_items += unique

# 2. Build the lazy stack: should take seconds and download nothing
t0 = time.perf_counter()
ds = load_lazy(all_items, ["B02", "B03", "B04", "B08", "SCL"])
print(f"\nBuilt lazy stack in {time.perf_counter() - t0:.1f} s")
print(ds)

b02 = ds.B02
print("\ndims            :", dict(b02.sizes))
print("dtype           :", b02.dtype)
print("chunks (y)      :", b02.chunks[1])
print("chunks (x)      :", b02.chunks[2])
print("tasks in graph  :", len(b02.data.__dask_graph__()))
print(f"size if loaded  : {ds.nbytes / 1e9:.2f} GB (all bands, as stored)")

# 3. Compute ONE small window across all dates (only the needed chunks are read)
win = b02.isel(x=slice(0, 256), y=slice(0, 256))
t0 = time.perf_counter()
arr = win.compute()
dt = time.perf_counter() - t0
print(f"\nComputed a 256x256 window for {arr.sizes['time']} dates: "
      f"{arr.nbytes / 1e6:.1f} MB in {dt:.1f} s")

# 4. A first taste of Day 9: median over time of that window (in memory now)
med = arr.where(arr > 0).median(dim="time", skipna=True)
refl = (med - 1000) / 10000
print(f"Blue reflectance, median over {arr.sizes['time']} dates: "
      f"mean {float(refl.mean()):.3f}, p5 {float(refl.quantile(0.05)):.3f}, "
      f"p95 {float(refl.quantile(0.95)):.3f}")
print("\nDo NOT call ds.B02.values on the full stack: that loads every date at once.")