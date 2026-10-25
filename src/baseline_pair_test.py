import numpy as np

from scene_io import compute_ndvi
from stack_utils import load_lazy, search_dates, to_reflectance

DATES = ["2022-06-24", "2022-07-14", "2022-07-19"]
BANDS = ["B02", "B03", "B04", "B08"]
raw, _ = search_dates("2022-06-01", "2022-07-31", 101)

def load_one(item):
    ds = load_lazy([item], BANDS + ["SCL"]).isel(time=0).compute()
    dn = np.nan_to_num(np.stack([ds[b].values for b in BANDS]), nan=0).astype("uint16")
    scl = np.nan_to_num(ds.SCL.values, nan=0).astype("uint8")
    return dn, scl


for d in DATES:
    pair = {it.properties["s2:processing_baseline"]: it
            for it in raw if it.properties["datetime"][:10] == d}
    if len(pair) < 2:
        print(d, "only one baseline:", list(pair))
        continue
    old, new = pair[min(pair, key=float)], pair[max(pair, key=float)]
    dn_o, scl_o = load_one(old)
    dn_n, scl_n = load_one(new)

    ok = ((dn_o > 0).all(axis=0) & (dn_n > 0).all(axis=0)
          & np.isin(scl_o, [4, 5]) & np.isin(scl_n, [4, 5]))
    ro, rn = to_reflectance(dn_o), to_reflectance(dn_n)

    print(f"\n{d}: baseline {min(pair, key=float)} vs {max(pair, key=float)}, {ok.sum():,} clear pixels")
    for k, b in enumerate(BANDS):
        print(f"  {b}: median (new - old) = {np.median((rn[k] - ro[k])[ok]):+.4f}")
    dd = (compute_ndvi(rn[3], rn[2]) - compute_ndvi(ro[3], ro[2]))[ok]
    med = np.median(dd)
    sig = 1.4826 * np.median(np.abs(dd - med))
    print(f"  NDVI: median shift {med:+.4f}, robust sigma {sig:.4f}, "
          f"share with |d| > 0.1: {(np.abs(dd) > 0.1).mean() * 100:.2f}%")