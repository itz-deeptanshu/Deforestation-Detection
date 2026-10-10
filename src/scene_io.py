from pathlib import Path

import numpy as np
import rasterio

from config import ROOT


def find_scene_path(date=None):
    """Path of a saved *_aoi.tif. date like '2022-07-09'; None = the latest file."""
    pattern = f"s2_{date}_*_aoi.tif" if date else "s2_*_aoi.tif"
    files = sorted((ROOT / "data" / "raw").glob(pattern))
    if not files:
        raise SystemExit("No saved scene found. Run src/load_scene.py first.")
    return files[-1]


def load_saved_scene(date=None):
    """Return (bands dict of reflectance, valid mask, scl array, meta dict)."""
    path = find_scene_path(date)
    with rasterio.open(path) as src:
        dn = src.read()                                   # (4, rows, cols) uint16
        names = src.descriptions                          # ('B02','B03','B04','B08')
        offset = float(src.tags().get("boa_offset", 1000))
        meta = {
            "path": path,
            "date": Path(path).name.split("_")[1],
            "transform": src.transform,
            "crs": src.crs,
            "offset": offset,
        }

    valid = (dn > 0).all(axis=0)                          # DN 0 = no data
    refl = (dn.astype("float32") - offset) / 10000.0      # float BEFORE subtracting
    refl[:, ~valid] = np.nan
    bands = dict(zip(names, refl))

    with rasterio.open(str(path).replace("_aoi.tif", "_scl.tif")) as src:
        scl = src.read(1)

    return bands, valid, scl, meta


def compute_ndvi(nir, red):
    """NDVI with divide-by-zero protection, clipped to [-1, 1]. NaN stays NaN."""
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (nir - red) / (nir + red)
    out[~np.isfinite(out)] = np.nan
    return np.clip(out, -1.0, 1.0)