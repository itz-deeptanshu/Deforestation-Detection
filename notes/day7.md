# Day 7 notes: review and buffer

## 1. Audit (audit_project.py)
All checks passed: 9 config keys present, threshold = 0.616, 3 scenes
(at the time of the audit) share shape (2500, 2500), origin (569630, 8879350)
and offset 1000, no data/figure/model files tracked by git, .gitignore covers
data/, outputs/, *.tif, *.qgz, notes day5 and day6 exist.
Note: the audit ran before the five extra scenes were fetched. Re-run it once
to confirm all 8 scenes pass.

## 2. Day 3 code test (test_day3.py)
All five assertions passed: 4 polygons with areas 3200 / 1500 / 0.09 / 0.01 ha,
MMU keeps 2, rasterize round trip has 0 mismatching pixels, overlay gives
1600 ha inside the reserve (34.0%), sjoin tags the full 3200 ha (overcounts
by 1600 ha). A 3200 ha polygon has "area" 0.00264 in EPSG:4326, which is
meaningless. The UserWarnings in the output are expected, because that
check deliberately measures area in degrees.
This closes the open item from Day 3: the polygonize/rasterize/overlay code
is verified and safe to reuse on Days 24-26.

## 3. Multi-date stats (scene_stats.py)
8 scenes, all single tile 20LNP, all on the same grid.

| date | base | blue | blue_p1 | red | NDVI med | forest% | AOT |
|---|---|---|---|---|---|---|---|
| 2022-07-09 | 4.0 | 0.044 | 0.013 | 0.083 | 0.498 | 28.06 | 0.064 |
| 2022-07-19 | 5.1 | 0.046 | 0.013 | 0.092 | 0.453 | 25.09 | 0.064 |
| 2022-07-29 | 5.1 | 0.061 | 0.026 | 0.108 | 0.388 | 20.08 | 0.135 |
| 2022-08-03 | 5.1 | 0.062 | 0.024 | 0.113 | 0.366 | 20.51 | 0.316 |
| 2024-07-13 | 5.1 | 0.056 | 0.021 | 0.107 | 0.400 | 21.84 | 0.082 |
| 2024-07-18 | 5.1 | 0.051 | 0.013 | 0.112 | 0.392 | 21.84 | 0.064 |
| 2024-07-23 | 5.11 | 0.058 | 0.021 | 0.117 | 0.367 | 20.26 | 0.070 |
| 2024-08-02 | 5.11 | 0.072 | 0.027 | 0.130 | 0.331 | 18.97 | 0.477 |

Year means: 2022 NDVI 0.427, forest 23.4%; 2024 NDVI 0.372, forest 20.7%.

Findings:
- Within-year drift is as large as the between-year gap. NDVI median falls
  from 0.498 to 0.366 across 25 days of 2022 alone, while the 2022-vs-2024
  difference in means is 0.055.
- Two scenes are hazy: 2022-08-03 (AOT 0.316) and 2024-08-02 (AOT 0.477).
  Blue p1 roughly doubles on hazy dates. 2022-07-29 (AOT 0.135, blue p1
  0.026) is borderline.
- The same 0.616 cutoff gives 19.0% to 28.1% forest depending on the date,
  with no land change. A fixed threshold is date-dependent.
- Clean dates only (AOT < 0.1): 2022 red 0.083-0.092 vs 2024 red 0.107-0.117.
  2024 is still redder (drier or browner ground), so part of the shift
  survives the haze filter. This could be real change, seasonal dryness,
  or both; the data cannot separate them.
- Confound: 2022-07-09 is processing baseline 04.00, every other scene is
  05.xx. The 07-09 -> 07-19 step (red 0.083 -> 0.092, same AOT) mixes drying
  and baseline. Not yet tested. [optional: fetch the 04.00 version of 2022-07-19]

Decision for Day 8:
- Select scenes by quality (AOT and blue p1), not calendar alone. Provisional
  rule: exclude scenes with AOT above about 0.15; review borderline 2022-07-29.
- Use medians across clean dates to reduce date-to-date drift.
- Deduplicate by date, preferring the newest baseline.
- Treat 2022-vs-2024 differences with caution until labels exist.

## 4. QGIS check of Day 5-6 outputs
- forest_mask: [is the 0.616 mask / needs rerun]. One-line check printed __ % forest
  (expected about 28.0; about 19.6 would mean the 0.72 mask). Looks like __.
- dndvi: shows __ over most of the area, strongest drops at __,
  west/east gradient [visible / not visible].
- patches: most outlines sit on __; I saw __ along the river and __ clusters
  in fields.

## 5. Day 6 patch tally
10 random (31, 81, 263, 245, 174, 97, 90, 143, 182, 309):
real clearing __, pasture/crop __, edge/mixed __, shadow/wet/burn __, unclear __.
5 largest (211, 191, 114, 318, 161): __.
Caveat: rough sample; patch counts are not hectares.

## 6. Week 1 checkpoint
Written in notes/week1_checkpoint.md: [done / not done].

## 7. Open items carried forward
- Deduplicate by date (prefer newest baseline) in Day 8
- Master grid: snap AOI outward to 10 m multiples (Day 8)
- Date selection by AOT / blue p1 (Day 8)
- Baseline 04.00 vs 05.xx effect untested
- Consider a second, more forested AOI (around Day 11)