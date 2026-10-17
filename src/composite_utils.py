import warnings

import numpy as np
import pandas as pd
from scipy import ndimage

from config import ROOT, load_config
from scene_io import compute_ndvi

CACHE = ROOT / "data" / "cache"
BANDS = ["B02", "B03", "B04", "B08"]
CORE_CLASSES = [3, 8, 9, 10]        # cloud shadow, cloud (medium/high), thin cirrus
OFFSET = 1000.0                     # all our scenes are baseline >= 04.00


def selected_dates(period_name):
    """Dates inside the period whose median AOT is <= scene_aot_max (from the Day 8 table)."""
    cfg = load_config()
    p = cfg[period_name]
    df = pd.read_csv(ROOT / "outputs" / "day8_scene_quality_both.csv")
    ok = (df["date"] >= p["start"]) & (df["date"] <= p["end"]) & (df["aot"] <= cfg["scene_aot_max"])
    return sorted(df.loc[ok, "date"].tolist())


def cache_paths(date):
    return CACHE / f"{date}_dn.npy", CACHE / f"{date}_scl.npy"


def load_cached(date):
    f_dn, f_scl = cache_paths(date)
    if not (f_dn.exists() and f_scl.exists()):
        raise SystemExit(f"No cache for {date}. Run: python src/cache_dates.py --period a")
    return np.load(f_dn), np.load(f_scl)


def masked_reflectance(date):
    """Reflectance (4, rows, cols) for one date with bad pixels set to NaN, plus the good mask."""
    cfg = load_config()
    dn, scl = load_cached(date)

    valid = (dn > 0).all(axis=0) & (scl > 0)
    core = np.isin(scl, CORE_CLASSES)
    if core.any():
        dist = ndimage.distance_transform_edt(~core)      # pixels to nearest cloud/shadow
        far = dist > cfg["cloud_dilate_px"]
    else:
        far = np.ones(scl.shape, dtype=bool)               # no cloud on this date
    good = valid & np.isin(scl, cfg["scl_keep"]) & far

    refl = (dn.astype("float32") - OFFSET) / 10000.0       # float BEFORE subtracting
    refl[:, ~good] = np.nan
    return refl, good


def build_composite(dates, min_obs):
    """Per-pixel median over dates. Returns (composite (4,r,c), count (r,c), per-date rows)."""
    cfg = load_config()
    thr = cfg["ndvi_forest_threshold"]
    n = len(dates)
    stack, count, rows = None, None, []

    for i, d in enumerate(dates):
        refl, good = masked_reflectance(d)
        if stack is None:
            stack = np.empty((n,) + refl.shape, dtype="float32")
            count = np.zeros(good.shape, dtype="uint8")
        stack[i] = refl
        count += good.astype("uint8")

        ndvi = compute_ndvi(refl[3], refl[2])
        ok = good & np.isfinite(ndvi)
        rows.append(dict(
            date=d,
            good_pct=good.mean() * 100,
            ndvi_med=float(np.median(ndvi[ok])) if ok.any() else np.nan,
            forest_pct=float((ndvi[ok] > thr).mean() * 100) if ok.any() else np.nan,
        ))

    comp = np.full(stack.shape[1:], np.nan, dtype="float32")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)   # "All-NaN slice" is expected
        for b in range(stack.shape[1]):
            comp[b] = np.nanmedian(stack[:, b], axis=0)
    comp[:, count < min_obs] = np.nan
    return comp, count, rows