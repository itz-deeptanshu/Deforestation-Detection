import numpy as np
import rasterio

from config import ROOT

path = ROOT / "data" / "raw" / "toy_ndvi_utm.tif"

with rasterio.open(path) as src:
    print("Driver     :", src.driver)
    print("Size       :", src.width, "cols x", src.height, "rows")
    print("Bands      :", src.count)
    print("Dtype      :", src.dtypes[0])
    print("CRS        :", src.crs)
    print("Nodata     :", src.nodata)
    print("Pixel size :", src.res)
    print("Bounds     :", src.bounds)
    print("Transform  :")
    print(src.transform)

    # --- Pixel <-> coordinate conversion ---
    print("\n--- Coordinates ---")
    corner_x, corner_y = src.transform * (0, 0)
    print("Top-left CORNER of pixel (0,0):", corner_x, corner_y)

    center_x, center_y = src.xy(0, 0)
    print("CENTER of pixel (0,0)         :", center_x, center_y)

    row, col = src.index(center_x, center_y)
    print("Back to row, col              :", row, col)

    # --- Reading data and nodata ---
    print("\n--- Nodata handling ---")
    raw = src.read(1)
    masked = src.read(1, masked=True)

    print("Raw min / mean      :", raw.min(), "/", round(float(raw.mean()), 4))
    print("Masked min / mean   :", round(float(masked.min()), 4), "/",
          round(float(masked.mean()), 4))
    print("Nodata pixel count  :", int((raw == src.nodata).sum()))

    # --- Values at known places ---
    print("\n--- Sample values ---")
    print("Inside forest   (row 1000, col 300):", round(float(raw[1000, 300]), 3))
    print("Inside clearing (row 700,  col 1000):", round(float(raw[700, 1000]), 3))
    print("In nodata corner (row 10, col 10)  :", raw[10, 10])