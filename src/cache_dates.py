import argparse
import time


import numpy as np

from composite_utils import BANDS, CACHE, cache_paths, selected_dates
from config import load_config
from stack_utils import load_lazy, search_dates

parser = argparse.ArgumentParser()
parser.add_argument("--period", choices=["a", "b"], required=True)
parser.add_argument("--limit", type=int, default=0, help="only the first N dates (quick test)")
args = parser.parse_args()

cfg = load_config()
name = f"period_{args.period}"
p = cfg[name]
dates = selected_dates(name)
if args.limit:
    dates = dates[:args.limit]
print(f"{name}: {len(dates)} dates selected (AOT <= {cfg['scene_aot_max']}):")
print(" ", dates)

# One deduplicated item per date (newest baseline); cloud filter off (101)
_, unique = search_dates(p["start"], p["end"], 101)
by_date = {it.properties["datetime"][:10]: it for it in unique}
missing = [d for d in dates if d not in by_date]
if missing:
    raise SystemExit(f"Not found in the archive: {missing}")

CACHE.mkdir(parents=True, exist_ok=True)
for i, d in enumerate(dates, 1):
    f_dn, f_scl = cache_paths(d)
    if f_dn.exists() and f_scl.exists():
        print(f"[{i}/{len(dates)}] {d}  already cached, skipping")
        continue

    t0 = time.perf_counter()
    ds = load_lazy([by_date[d]], BANDS + ["SCL"]).isel(time=0).compute()
    dn = np.nan_to_num(np.stack([ds[b].values for b in BANDS]), nan=0).astype("uint16")
    scl = np.nan_to_num(ds.SCL.values, nan=0).astype("uint8")

    # Write to a temporary name first, so an interrupted run never leaves a half-written file
    for arr, final in ((dn, f_dn), (scl, f_scl)):
        tmp = final.with_name(final.name + ".tmp")
        with open(tmp, "wb") as f:
            np.save(f, arr)
        tmp.replace(final)

    print(f"[{i}/{len(dates)}] {d}  baseline {by_date[d].properties.get('s2:processing_baseline')}"
          f"  shape {dn.shape}  valid {(dn > 0).all(axis=0).mean() * 100:.1f}%"
          f"  {time.perf_counter() - t0:.0f} s", flush=True)

print("\nCached to:", CACHE)