import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

from config import ROOT, load_config
from stack_utils import master_geobox

RAW = ROOT / "data" / "labels" / "raw"
OUT = ROOT / "data" / "labels"
IGNORE = 255
WC_TREE = 10


def on_master(name):
    """Read a raw label raster onto the master grid with nearest neighbor."""
    gb, cfg = master_geobox(), load_config()
    with rasterio.open(RAW / f"{name}.tif") as src:
        dst = np.zeros(tuple(gb.shape), dtype=src.dtypes[0])
        reproject(source=rasterio.band(src, 1), destination=dst,
                  dst_transform=gb.affine, dst_crs=f"EPSG:{cfg['utm_epsg']}",
                  resampling=Resampling.nearest)
    return dst


def _reasons(h, w, amb, special):
    """Why a pixel is ignored (0 = it has a label). Later assignments win."""
    r = np.zeros(h.shape, dtype="uint8")
    r[h & ~w] = 3              # Hansen says forest, WorldCover does not
    r[~h & w] = 4              # WorldCover says tree, Hansen does not
    r[amb] = 2                 # loss in the composite's own year
    r[special] = 1             # Hansen gain or Hansen no-data
    return r


def _label(h, w, amb, special):
    lab = np.full(h.shape, IGNORE, dtype="uint8")
    lab[h & w] = 1
    lab[~h & ~w] = 0
    lab[amb | special] = IGNORE
    return lab


def build_labels():
    """Return label_A, label_B, label_change and the pieces they are built from."""
    T = load_config()["forest_canopy_min"]
    tc, ly = on_master("hansen_treecover2000"), on_master("hansen_lossyear")
    gain, dm = on_master("hansen_gain"), on_master("hansen_datamask")
    wc21 = on_master("worldcover_2021")

    land = dm == 1
    base = land & (tc >= T)                       # forest in 2000
    wc_tree = wc21 == WC_TREE
    special = (gain == 1) | (dm == 0)

    def hansen_forest(end_year):                  # forest at the END of end_year
        return base & ~((ly >= 1) & (ly <= end_year - 2000))

    def wc_forest(end_year):                      # WorldCover 2021 carried forward with Hansen loss
        return wc_tree & ~((ly >= 22) & (ly <= end_year - 2000))

    h_a, w_a = hansen_forest(2021), wc_forest(2021)
    h_b, w_b = hansen_forest(2023), wc_forest(2023)
    amb_a = base & (ly == 22)                     # ambiguous for composite A
    amb_b = base & (ly == 24)                     # ambiguous for composite B

    lab_a = _label(h_a, w_a, amb_a, special)
    lab_b = _label(h_b, w_b, amb_b, special)

    chg = np.full(lab_a.shape, IGNORE, dtype="uint8")
    chg[(lab_a == 1) & (lab_b == 1)] = 0
    chg[(lab_a == 1) & (lab_b == 0)] = 1

    return dict(A=lab_a, B=lab_b, change=chg,
                reason_A=_reasons(h_a, w_a, amb_a, special),
                reason_B=_reasons(h_b, w_b, amb_b, special),
                h_A=h_a, w_A=w_a, h_B=h_b, w_B=w_b,
                gain=gain == 1, ly=ly, base=base)