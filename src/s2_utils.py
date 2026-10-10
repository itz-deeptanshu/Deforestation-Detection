import geopandas as gpd
import planetary_computer
import pystac_client
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import from_bounds
from shapely.geometry import mapping
import numpy as np

from config import ROOT, load_config

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

# GDAL settings that make reading remote COGs faster and more robust
GDAL_ENV = dict(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
    GDAL_HTTP_MAX_RETRY="3",
    GDAL_HTTP_RETRY_DELAY="2",
)


def load_aoi_4326():
    """Return the AOI polygon (shapely) in lon/lat."""
    cfg = load_config()
    gdf = gpd.read_file(ROOT / cfg["aoi_path"]).to_crs(epsg=4326)
    return gdf.geometry.iloc[0]


def aoi_bounds_in(crs):
    """AOI bounding box (minx, miny, maxx, maxy) expressed in the given CRS."""
    aoi = gpd.GeoSeries([load_aoi_4326()], crs="EPSG:4326").to_crs(crs)
    return tuple(float(v) for v in aoi.total_bounds)


def get_catalog():
    """Open the Planetary Computer STAC catalog; links are signed automatically."""
    return pystac_client.Client.open(
        STAC_URL, modifier=planetary_computer.sign_inplace
    )


def search_items(start, end, max_cloud):
    """Find Sentinel-2 L2A scenes touching the AOI in a date range."""
    search = get_catalog().search(
        collections=["sentinel-2-l2a"],
        intersects=mapping(load_aoi_4326()),
        datetime=f"{start}/{end}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
    )
    return list(search.item_collection())


def read_band(href):
    """Read one 10 m band clipped to the AOI. Returns (array, transform, crs)."""
    with rasterio.Env(**GDAL_ENV), rasterio.open(href) as src:
        bounds = aoi_bounds_in(src.crs)
        window = from_bounds(*bounds, transform=src.transform)
        window = window.round_offsets().round_lengths()
        data = src.read(1, window=window)
        return data, src.window_transform(window), src.crs


def read_on_grid(href, shape, transform, crs, resampling=Resampling.nearest):
    """Read a band (e.g. 20 m SCL) and resample it onto a given 10 m grid."""
    dst = np.zeros(shape, dtype="uint8")
    with rasterio.Env(**GDAL_ENV), rasterio.open(href) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            dst_transform=transform,
            dst_crs=crs,
            resampling=resampling,
        )
    return dst