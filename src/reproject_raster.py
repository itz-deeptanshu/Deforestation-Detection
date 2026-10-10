import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject

from config import ROOT

src_path = ROOT / "data" / "raw" / "toy_ndvi_utm.tif"
dst_path = ROOT / "data" / "raw" / "toy_ndvi_4326.tif"
dst_crs = "EPSG:4326"

with rasterio.open(src_path) as src:
    # 1. Work out the new grid
    transform, width, height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds
    )

    # 2. Copy the metadata and update it
    meta = src.meta.copy()
    meta.update(crs=dst_crs, transform=transform, width=width, height=height,
                compress="deflate")

    print("BEFORE: CRS", src.crs, "| pixel", src.res, "| size", src.width, "x", src.height)
    print("AFTER : CRS", dst_crs, "| pixel", (round(transform.a, 7), round(-transform.e, 7)),
          "| size", width, "x", height)

    # 3. Reproject band 1
    with rasterio.open(dst_path, "w", **meta) as dst:
        reproject(
            source=rasterio.band(src, 1),
            destination=rasterio.band(dst, 1),
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
        )

print("Saved:", dst_path)