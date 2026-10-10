import geopandas as gpd

from config import ROOT, load_config

cfg = load_config()

aoi = gpd.read_file(ROOT / cfg["aoi_path"])

minx, miny, maxx, maxy = aoi.total_bounds
file_bbox = [round(v, 4) for v in (minx, miny, maxx, maxy)]
print("bbox in config.yaml :", cfg["bbox"])
print("bbox in aoi file    :", file_bbox)

same = all(abs(a - b) < 1e-3 for a, b in zip(cfg["bbox"], file_bbox))
print("Result:", "MATCH" if same else "MISMATCH - fix config.yaml")

aoi_utm = aoi.to_crs(epsg=cfg["utm_epsg"])
print("Area (km2):", round(aoi_utm.area.iloc[0] / 1e6, 3))

print("Period A:", cfg["period_a"])
print("Period B:", cfg["period_b"])