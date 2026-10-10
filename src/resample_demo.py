import numpy as np
import rasterio
from rasterio.enums import Resampling

from config import ROOT

path = ROOT / "data" / "raw" / "toy_ndvi_utm.tif"
scale = 3   # make pixels 3x bigger: 10 m -> about 30 m

with rasterio.open(path) as src:
    new_h = src.height // scale
    new_w = src.width // scale
    print(f"Original: {src.height} x {src.width}   New: {new_h} x {new_w}")

    # ---------- Part 1: continuous data (NDVI) ----------
    ndvi_bilinear = src.read(
        1, out_shape=(new_h, new_w), resampling=Resampling.bilinear
    )
    ndvi_nearest = src.read(
        1, out_shape=(new_h, new_w), resampling=Resampling.nearest
    )

    # The new transform: pixels are bigger, so scale the old transform
    new_transform = src.transform * src.transform.scale(
        src.width / new_w, src.height / new_h
    )
    print("New pixel size:", round(new_transform.a, 2), "m")

    # ---------- Part 2: categorical data (forest mask) ----------
    raw = src.read(1)
    forest_mask = (raw > 0.5).astype("float32")      # 1 = forest, 0 = not

    mask_nearest = src.read(1, out_shape=(new_h, new_w), resampling=Resampling.nearest)
    # Build the mask at full size first, then resample it two ways
    # (we resample the mask array, not the file, so use a MemoryFile-free trick)

# Resample the in-memory mask by simple block logic for comparison
import rasterio.warp
from rasterio.transform import Affine

def resample_array(arr, src_transform, new_shape, method):
    dst = np.zeros(new_shape, dtype="float32")
    dst_transform = src_transform * Affine.scale(arr.shape[1] / new_shape[1],
                                                 arr.shape[0] / new_shape[0])
    rasterio.warp.reproject(
        source=arr, destination=dst,
        src_transform=src_transform, src_crs="EPSG:32720",
        dst_transform=dst_transform, dst_crs="EPSG:32720",
        resampling=method,
    )
    return dst

with rasterio.open(path) as src:
    t = src.transform

mask_near = resample_array(forest_mask, t, (new_h, new_w), Resampling.nearest)
mask_bil = resample_array(forest_mask, t, (new_h, new_w), Resampling.bilinear)

print("\nForest MASK after resampling:")
print("  nearest  unique values:", np.unique(mask_near))
print("  bilinear unique values:", len(np.unique(mask_bil)), "different values")
print("  bilinear sample values:", np.unique(mask_bil)[:6])