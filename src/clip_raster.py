import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import rasterio.mask
from shapely.geometry import mapping

from config import ROOT, load_config

cfg = load_config()
src_path = ROOT / "data" / "raw" / "toy_ndvi_utm.tif"
dst_path = ROOT / "data" / "raw" / "toy_ndvi_clip.tif"

# 1. Build a clip polygon: a circle of 4 km radius around the AOI center
aoi = gpd.read_file(ROOT / cfg["aoi_path"]).to_crs(epsg=cfg["utm_epsg"])
circle = aoi.geometry.centroid.buffer(4000)

with rasterio.open(src_path) as src:
    # 2. Safety check: polygon and raster must share a CRS
    clip_gdf = gpd.GeoDataFrame(geometry=circle, crs=aoi.crs)
    clip_gdf = clip_gdf.to_crs(src.crs)
    shapes = [mapping(g) for g in clip_gdf.geometry]

    # 3. Clip
    clipped, clipped_transform = rasterio.mask.mask(
        src, shapes, crop=True, nodata=src.nodata
    )

    meta = src.meta.copy()
    meta.update(height=clipped.shape[1], width=clipped.shape[2],
                transform=clipped_transform, compress="deflate")

    original = src.read(1, masked=True)

print("Original shape:", original.shape)
print("Clipped shape :", clipped.shape, "(bands, rows, cols)")
print("Clipped transform origin:", clipped_transform.c, clipped_transform.f)

# 4. Save
with rasterio.open(dst_path, "w", **meta) as dst:
    dst.write(clipped)

# 5. Plot before and after
clipped_masked = np.ma.masked_equal(clipped[0], meta["nodata"])

fig, axes = plt.subplots(1, 2, figsize=(11, 5))
axes[0].imshow(original, cmap="RdYlGn", vmin=0, vmax=1)
axes[0].set_title("Original")
im = axes[1].imshow(clipped_masked, cmap="RdYlGn", vmin=0, vmax=1)
axes[1].set_title("Clipped to 4 km circle")
fig.colorbar(im, ax=axes, shrink=0.8, label="fake NDVI")

out_png = ROOT / "outputs" / "day2_clip.png"
out_png.parent.mkdir(exist_ok=True)
fig.savefig(out_png, dpi=120)
print("Saved figure:", out_png)
plt.show()