import subprocess
from pathlib import Path

import numpy as np
import rasterio

from config import ROOT, load_config

problems = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label} {detail}")
    if not ok:
        problems.append(label)


# ---------- 1. Config ----------
cfg = load_config()
for key in ["aoi_path", "bbox", "utm_epsg", "resolution_m", "period_a", "period_b",
            "max_scene_cloud_pct", "ndvi_forest_threshold", "reference_date"]:
    check(key in cfg, f"config key '{key}'", f"= {cfg.get(key)}")
check(cfg.get("ndvi_forest_threshold") == 0.616, "forest threshold is the documented 0.616")

# ---------- 2. Every saved Sentinel-2 scene shares one grid ----------
files = sorted((ROOT / "data" / "raw").glob("s2_20*_aoi.tif"))
check(len(files) >= 3, "at least 3 saved scenes", f"({len(files)} found)")

ref = None
for f in files:
    with rasterio.open(f) as src:
        t, shape, crs = src.transform, (src.height, src.width), src.crs
        tags, count, nodata = src.tags(), src.count, src.nodata
    scl = f.with_name(f.name.replace("_aoi.tif", "_scl.tif"))
    if ref is None:
        ref = (t, shape, crs)
    same = (t == ref[0]) and (shape == ref[1]) and (crs == ref[2])
    on_grid = (t.c % 10 == 0) and (t.f % 10 == 0)
    check(same and on_grid and count == 4 and nodata == 0 and "boa_offset" in tags
          and scl.exists(),
          f"scene {f.name}",
          f"shape {shape}, origin ({t.c:.0f}, {t.f:.0f}), offset {tags.get('boa_offset')}")

# ---------- 3. Git hygiene ----------
tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                         cwd=ROOT).stdout.split("\n")
bad = [p for p in tracked if p.lower().endswith((".tif", ".tiff", ".gpkg", ".png", ".qgz", ".pt"))]
check(not bad, "no data/figure/model files tracked by git", f"{bad[:5] if bad else ''}")

ignore = (ROOT / ".gitignore").read_text()
for pattern in ["data/", "outputs/", "*.tif", "*.qgz"]:
    check(pattern in ignore, f".gitignore contains {pattern}")

# ---------- 4. Notes ----------
for n in ["day5.md", "day6.md"]:
    check((ROOT / "notes" / n).exists(), f"notes/{n} exists")

print()
print("ALL CHECKS PASSED" if not problems else f"{len(problems)} problem(s): {problems}")