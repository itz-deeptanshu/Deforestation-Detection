import numpy as np
import rasterio
import geopandas as gpd
from rasterio.transform import from_origin

from config import ROOT, load_config

cfg = load_config()
res = cfg["resolution_m"]
nodata = -9999.0

# 1. Get the AOI in meters (UTM)
aoi = gpd.read_file(ROOT / cfg["aoi_path"]).to_crs(epsg=cfg["utm_epsg"])
minx, miny, maxx, maxy = aoi.total_bounds

# 2. Work out the grid size
width = int(round((maxx - minx) / res))
height = int(round((maxy - miny) / res))
print("Grid size (cols x rows):", width, "x", height)

# 3. Build the transform: top-left corner is (minx, maxy)
transform = from_origin(minx, maxy, res, res)

# 4. Fake NDVI: forest everywhere, plus two cleared rectangles
rng = np.random.default_rng(42)
data = rng.normal(0.80, 0.03, size=(height, width)).astype("float32")
data[500:900, 600:1400] = rng.normal(0.20, 0.03, size=(400, 800))
data[1500:1800, 200:700] = rng.normal(0.25, 0.03, size=(300, 500))

# 5. A nodata corner, like the edge of a satellite swath
data[:100, :100] = nodata

# 6. Write the GeoTIFF
out_path = ROOT / "data" / "raw" / "toy_ndvi_utm.tif"
out_path.parent.mkdir(parents=True, exist_ok=True)

with rasterio.open(
    out_path, "w",
    driver="GTiff",
    height=height, width=width,
    count=1,
    dtype="float32",
    crs=f"EPSG:{cfg['utm_epsg']}",
    transform=transform,
    nodata=nodata,
    compress="deflate",
) as dst:
    dst.write(data, 1)

print("Saved:", out_path)