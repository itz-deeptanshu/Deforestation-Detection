from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

# ---------- Settings you can change ----------
CENTER_LON = -62.25     # longitude of the center (x). Negative = west.
CENTER_LAT = -10.25     # latitude of the center (y). Negative = south.
SIZE_KM = 25            # side length of the square in kilometers
# ---------------------------------------------

ROOT = Path(__file__).resolve().parents[1]      # the project root folder
OUT_FILE = ROOT / "aoi" / "aoi.geojson"

# 1. Make a one-point GeoDataFrame in EPSG:4326 (lon/lat degrees)
center = gpd.GeoDataFrame(geometry=[Point(CENTER_LON, CENTER_LAT)], crs="EPSG:4326")

# 2. Ask geopandas which UTM zone fits this location
utm_crs = center.estimate_utm_crs()
print("UTM CRS      :", utm_crs.to_epsg())

# 3. Convert the point to meters
center_utm = center.to_crs(utm_crs)

# 4. Buffer the point by half the side length, with square corners
half_side_m = SIZE_KM * 1000 / 2
square_utm = center_utm.buffer(half_side_m, cap_style="square")

# 5. Sanity check: the area should be 625 km2
print("Area (km2)   :", round(square_utm.area.iloc[0] / 1e6, 3))

# 6. Put the square in a GeoDataFrame and convert back to degrees
aoi = gpd.GeoDataFrame({"name": ["aoi_rondonia"]}, geometry=square_utm.values, crs=utm_crs)
aoi = aoi.to_crs("EPSG:4326")

# 7. Save as GeoJSON
OUT_FILE.parent.mkdir(exist_ok=True)
aoi.to_file(OUT_FILE, driver="GeoJSON")
print("Saved        :", OUT_FILE)

# 8. Print the bounding box so we can copy it into config.yaml
minx, miny, maxx, maxy = aoi.total_bounds
print("bbox [min_lon, min_lat, max_lon, max_lat]:",
      [round(v, 4) for v in (minx, miny, maxx, maxy)])