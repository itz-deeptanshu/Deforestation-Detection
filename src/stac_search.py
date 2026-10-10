import pandas as pd
from shapely.geometry import shape

from config import ROOT, load_config
from s2_utils import get_catalog, load_aoi_4326, search_items

cfg = load_config()
aoi = load_aoi_4326()
max_cloud = cfg["max_scene_cloud_pct"]

print("Catalog:", get_catalog().title)

rows = []
first_item = None

for name in ("period_a", "period_b"):
    period = cfg[name]
    items = search_items(period["start"], period["end"], max_cloud)
    print(f"{name}: {period['start']} -> {period['end']} | "
          f"{len(items)} scenes with cloud < {max_cloud}%")

    for it in items:
        p = it.properties
        rows.append({
            "period": name,
            "id": it.id,
            "date": p["datetime"][:10],
            "tile": p.get("s2:mgrs_tile"),
            "orbit": p.get("sat:relative_orbit"),
            "cloud": round(p["eo:cloud_cover"], 1),
            "baseline": p.get("s2:processing_baseline"),
            "covers_aoi": shape(it.geometry).contains(aoi),
        })
        if first_item is None:
            first_item = it

if not rows:
    raise SystemExit("No scenes found. Check dates, cloud threshold, and internet.")

df = pd.DataFrame(rows).sort_values(["period", "date"]).reset_index(drop=True)

print("\n--- All scenes ---")
print(df[["period", "date", "tile", "orbit", "cloud", "baseline", "covers_aoi"]]
      .to_string(index=False))

print("\n--- Summary per period and tile ---")
summary = df.groupby(["period", "tile"]).agg(
    scenes=("id", "count"),
    mean_cloud=("cloud", "mean"),
    fully_cover_aoi=("covers_aoi", "sum"),
).round(1)
print(summary)

print("\n--- Revisit gaps ---")
for name, g in df.groupby("period"):
    days = pd.to_datetime(g["date"]).drop_duplicates().sort_values()
    print(f"{name}: {len(days)} distinct dates, "
          f"median gap {days.diff().dt.days.median()} days")

out = ROOT / "outputs" / "day4_scenes.csv"
out.parent.mkdir(exist_ok=True)
df.to_csv(out, index=False)
print("\nSaved:", out)

# --- Look inside one item ---
print("\n--- One item in detail ---")
print("ID        :", first_item.id)
print("Collection:", first_item.collection_id)
print("Footprint :", first_item.bbox)
print("Assets    :", len(first_item.assets))
for key in ["B02", "B03", "B04", "B08", "SCL", "visual"]:
    a = first_item.assets[key]
    print(f"  {key:7s} {a.media_type}  {a.href.split('?')[0]}")