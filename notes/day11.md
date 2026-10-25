# Day 11 notes: label sources and forest definition

## Sources
- Hansen GFC GFC-2025-v1.13 (CC BY 4.0, 30 m): canopy 2000, loss year 2001-2025, gain, datamask. Tile 10S_070W.
  2011-2025 data uses an updated methodology (per the v1.13 documentation).
- ESA WorldCover 2020 (v1.0.0) and 2021 (v2.0.0) via Planetary Computer (10 m). Different algorithms between years.
- Not used now: Dynamic World (derived from Sentinel-2, needs Earth Engine), MapBiomas, PRODES, GLAD/RADD
  (reserved for validation, Day 26).

## Forest definition (chosen before seeing the sweep)
Forest at a composite date = Hansen canopy in 2000 >= 30% AND land AND no loss recorded before that composite's year.
Ambiguous (planned "ignore" = 255): loss in the composite's own year (2022 for A, 2024 for B);
pixels with Hansen gain; pixels where Hansen and WorldCover 2021 disagree (decision on Day 12).
Strict new clearing between A and B = loss year 2023 only.
Not separated: plantations; regrowth after 2000 is invisible in Hansen (check against WorldCover).
Minimum mapping unit 0.5 ha (applied to detections, not labels).

## Results
Window sizes: Hansen __ , WorldCover __.
Hansen forest in 2000 (>= 30%): __ ha (__% of AOI). Forest at A (end 2021): __ ha.
WorldCover 2021 tree cover: __%. Main non-tree classes: __.
Hansen vs WorldCover 2020 at 30%: IoU __ (both __ ha, Hansen only __, WorldCover only __).
Canopy sensitivity: forest ha at 10% / 30% / 50% / 70% = __ / __ / __ / __.
Hansen loss (forest-2000 pixels): 2022 __ ha, 2023 __ ha, 2024 __ ha. Day 6 upper bound was 886 ha.
NDVI-forest (composite A, 0.616) vs Hansen end-2021: precision __, recall __. vs WorldCover 2021: precision __, recall __.

## Observations
- Loss pattern: [compact blocks / scattered pixels], mostly [near the river / in fields].
- Disagreement between sources sits [along edges / in fields / near the river].

## Limits
- Weak labels: 30 m, Landsat-based, loss includes fire and logging.
- Hansen 30 m resampled to 10 m is blocky and may be offset by up to ~15 m.
- 2022 and 2024 loss years are ambiguous relative to our June-July composites.
- WorldCover 2020 and 2021 are not comparable as change.

## Next
Day 12: align labels to the master grid, build label_A and label_B with ignore values.