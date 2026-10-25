import json
import math

import planetary_computer
import pystac_client
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape

from config import ROOT, load_config
from s2_utils import GDAL_ENV, STAC_URL, load_aoi_4326

cfg = load_config()
OUT = ROOT / "data" / "labels" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

aoi = load_aoi_4326()
minx, miny, maxx, maxy = aoi.bounds
PAD = 0.002                      # degrees (~220 m) so the window surely covers the AOI
bounds = (minx - PAD, miny - PAD, maxx + PAD, maxy + PAD)
sources = {}


def save_window(href, out_path):
    """Read only the AOI window of a remote GeoTIFF (EPSG:4326) and save it locally."""
    with rasterio.Env(**GDAL_ENV), rasterio.open(href) as src:
        assert src.crs.to_epsg() == 4326, f"unexpected CRS {src.crs}"
        window = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
        data = src.read(1, window=window)
        profile = dict(driver="GTiff", height=data.shape[0], width=data.shape[1], count=1,
                       dtype=data.dtype, crs=src.crs, transform=src.window_transform(window),
                       nodata=src.nodata, compress="deflate")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data, 1)
    return data


# ---------- 1. ESA WorldCover from Planetary Computer ----------
print("=== ESA WorldCover ===")
catalog = pystac_client.Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
items = list(catalog.search(collections=["esa-worldcover"], intersects=mapping(aoi),
                            datetime="2020-01-01/2021-12-31").item_collection())
items = [it for it in items if shape(it.geometry).contains(aoi)]
by_year = {}
for it in items:
    year = (it.properties.get("start_datetime") or it.properties["datetime"])[:4]
    by_year.setdefault(year, []).append(it)
    print(f"  {it.id}  year {year}  version {it.properties.get('esa_worldcover:product_version')}")

for year in ("2020", "2021"):
    if len(by_year.get(year, [])) != 1:
        raise SystemExit(f"Expected exactly 1 WorldCover tile for {year}, found "
                         f"{len(by_year.get(year, []))}. Send me the list above.")
    it = by_year[year][0]
    data = save_window(it.assets["map"].href, OUT / f"worldcover_{year}.tif")
    vals, counts = zip(*sorted(zip(*[a.tolist() for a in __import__('numpy').unique(data, return_counts=True)])))
    print(f"  {year}: window {data.shape}, classes present {list(vals)}")
    sources[f"worldcover_{year}"] = dict(item=it.id,
                                         version=it.properties.get("esa_worldcover:product_version"))

# ---------- 2. Hansen Global Forest Change ----------
print("\n=== Hansen Global Forest Change ===")
ver = cfg["hansen_version"]
lat_top = math.ceil(maxy / 10) * 10
lon_left = math.floor(minx / 10) * 10
assert miny >= lat_top - 10 and maxx <= lon_left + 10, "AOI spans two Hansen tiles; tell me"
tile = (f"{abs(lat_top):02d}{'N' if lat_top >= 0 else 'S'}_"
        f"{abs(lon_left):03d}{'E' if lon_left >= 0 else 'W'}")
print("  tile:", tile)

failed = []
for layer in ("treecover2000", "lossyear", "gain", "datamask"):
    url = (f"https://storage.googleapis.com/earthenginepartners-hansen/{ver}/"
           f"Hansen_{ver}_{layer}_{tile}.tif")
    try:
        data = save_window(url, OUT / f"hansen_{layer}.tif")
        print(f"  {layer}: window {data.shape}, min {data.min()}, max {data.max()}")
        sources[f"hansen_{layer}"] = dict(url=url)
    except Exception as exc:
        failed.append((layer, url, str(exc)[:120]))
        print(f"  {layer}: FAILED ({str(exc)[:120]})")

(OUT / "sources.json").write_text(json.dumps(sources, indent=2))
if failed:
    print("\nSome Hansen layers failed. Download those files by hand (a few hundred MB each),")
    print("then I will give you a one-line script to cut the AOI window out of them:")
    for layer, url, _ in failed:
        print(" ", url)
else:
    print("\nAll labels saved to", OUT)