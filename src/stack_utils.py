import math
from datetime import date as Date
from datetime import timedelta

import geopandas as gpd
import odc.stac
import planetary_computer
import pystac_client
from odc.geo.geobox import GeoBox
from shapely.geometry import mapping

from config import ROOT, load_config
from s2_utils import STAC_URL, load_aoi_4326

def master_geobox():
    """The one grid every Day 8+ dataset is read onto (AOI snapped outward to 10 m)."""
    cfg = load_config()
    res = cfg["resolution_m"]
    aoi = gpd.read_file(ROOT / cfg["aoi_path"]).to_crs(epsg=cfg["utm_epsg"])
    minx, miny, maxx, maxy = aoi.total_bounds
    left = float(math.floor(minx / res) * res)
    bottom = float(math.floor(miny / res) * res)
    right = float(math.ceil(maxx / res) * res)
    top = float(math.ceil(maxy / res) * res)
    return GeoBox.from_bbox((left, bottom, right, top),
                            crs=f"EPSG:{cfg['utm_epsg']}", resolution=res)


def dedupe_by_date(items):
    """One item per (date, tile): keep the highest processing baseline."""
    best = {}
    for it in items:
        key = (it.properties["datetime"][:10], it.properties.get("s2:mgrs_tile"))
        baseline = float(it.properties.get("s2:processing_baseline", "0"))
        if key not in best or baseline > best[key][0]:
            best[key] = (baseline, it)
    return [best[k][1] for k in sorted(best)]


def search_dates(start, end, max_cloud):
    """Return (raw items, deduplicated items). The catalog is UNSIGNED on purpose."""
    catalog = pystac_client.Client.open(STAC_URL)
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects=mapping(load_aoi_4326()),
        datetime=f"{start}/{end}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
    )
    raw = list(search.item_collection())
    return raw, dedupe_by_date(raw)


def get_item_for_date(date):
    """The single deduplicated item for one acquisition date, e.g. '2022-07-09'."""
    day = Date.fromisoformat(date)
    _, unique = search_dates(day.isoformat(), (day + timedelta(days=1)).isoformat(), 101)
    unique = [it for it in unique if it.properties["datetime"][:10] == date]
    if not unique:
        raise SystemExit(f"No scene on {date}. Pick a date from outputs/day4_scenes.csv.")
    return unique[0]


def load_lazy(items, bands, chunk=1024):
    """Lazy (Dask-backed) xarray Dataset on the master grid. No pixels are read yet."""
    for it in items:
        baseline = float(it.properties.get("s2:processing_baseline", "0"))
        if baseline < 4.0:
            raise SystemExit(f"{it.id}: baseline {baseline} < 4.0, offset logic would be wrong.")
    odc.stac.configure_rio(cloud_defaults=True)
    return odc.stac.load(
        items,
        bands=bands,
        geobox=master_geobox(),
        chunks={"x": chunk, "y": chunk},
        resampling="nearest",
        patch_url=planetary_computer.sign,      # sign URLs at READ time (A3)
    )


def to_reflectance(dn, offset=1000.0):
    """DN -> reflectance. Mask no-data (DN == 0) BEFORE calling this, and set it NaN after."""
    return (dn.astype("float32") - offset) / 10000.0