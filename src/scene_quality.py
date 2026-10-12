import argparse

import numpy as np
import pandas as pd

from config import ROOT, load_config
from stack_utils import load_lazy, search_dates

parser = argparse.ArgumentParser()
parser.add_argument("--period", choices=["a", "b", "both"], default="both")
parser.add_argument("--limit", type=int, default=0, help="only the first N dates (for a quick test)")
args = parser.parse_args()

cfg = load_config()
aot_max = cfg["scene_aot_max"]
names = {"a": ["period_a"], "b": ["period_b"], "both": ["period_a", "period_b"]}[args.period]

items = []
for name in names:
    p = cfg[name]
    _, unique = search_dates(p["start"], p["end"], cfg["max_scene_cloud_pct"])
    items += unique
if args.limit:
    items = items[:args.limit]
by_date = {it.properties["datetime"][:10]: it for it in items}
print(f"{len(items)} unique dates. Each is downloaded once (B02, SCL, AOT); this takes a while.\n")

ds = load_lazy(items, ["B02", "SCL", "AOT"])

rows = []
for i, ts in enumerate(ds.time.values):
    day = str(ts)[:10]
    it = by_date[day]
    sl = ds.isel(time=i).compute()                 # the only moment pixels are read
    b02 = np.nan_to_num(sl.B02.values, nan=0).astype("uint16")
    scl = np.nan_to_num(sl.SCL.values, nan=0).astype("uint8")
    aot_raw = np.nan_to_num(sl.AOT.values, nan=0).astype("uint16")
    valid = (b02 > 0) & (scl > 0)
    n = max(int(valid.sum()), 1)
    clear = valid & np.isin(scl, [4, 5])
    blue = (b02.astype("float32") - 1000.0) / 10000.0
    aot = aot_raw[aot_raw > 0].astype("float32") / 1000.0

    def pct(mask):
        return float(mask.sum()) / n * 100

    row = dict(
        date=day,
        base=it.properties.get("s2:processing_baseline"),
        scene_cloud=round(it.properties["eo:cloud_cover"], 1),
        clear=pct(clear),
        cloud=pct(np.isin(scl, [8, 9, 10])),
        shadow=pct(scl == 3),
        dark2=pct(scl == 2),
        uncl7=pct(scl == 7),
        aot=float(np.median(aot)) if aot.size else np.nan,
        blue_p1=float(np.percentile(blue[clear], 1)) if clear.any() else np.nan,
    )
    rows.append(row)
    print(f"[{i + 1:2d}/{len(items)}] {day}  AOT {row['aot']:.3f}  clear {row['clear']:5.1f}%  "
          f"cloud {row['cloud']:5.1f}%", flush=True)

df = pd.DataFrame(rows)
df["usable"] = df["aot"] <= aot_max

print(f"\nProvisional rule: usable if median AOT <= {aot_max}\n")
print(df.round(3).to_string(index=False))

df["month"] = df["date"].str[:7]
summary = df.groupby("month").agg(dates=("date", "count"), usable=("usable", "sum"))
print("\nDates per month (total / usable):")
print(summary.to_string())

out = ROOT / "outputs" / f"day8_scene_quality_{args.period}.csv"
out.parent.mkdir(exist_ok=True)
df.to_csv(out, index=False)
print("\nSaved:", out)