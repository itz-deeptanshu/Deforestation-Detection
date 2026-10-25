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
Windows: Hansen (922, 931), WorldCover (2767, 2794). Master grid 62,550 ha.
Hansen forest in 2000 (>= 30%): 24,702 ha (39.5% of AOI). Forest at A (no loss through 2021): 12,617 ha (20.2%).
WorldCover tree cover: 21.9% (2020), 25.2% (2021). Non-tree: 74-77% grassland; all other classes < 1% each.
Hansen (end 2020) vs WorldCover 2020 at 30%: both 8,749 ha, Hansen only 4,134, WorldCover only 4,954,
neither 44,712; IoU 0.490. Disagreement 9,088 ha = 14.5% of the AOI.
Canopy sensitivity (Hansen ha / IoU): 10% 14,810 / 0.471; 30% 12,884 / 0.490; 50% 11,296 / 0.501; 70% 9,546 / 0.498.
Agreement is flat across thresholds, so disagreement is not a threshold effect.
51.6% of 2000 forest lost by 2025 (6.5% in 2001, 16.2% cumulative by 2002, 32.9% by 2006).
Recent loss (forest-2000 pixels): 2022 294 ha, 2023 186 ha, 2024 73 ha, 2025 97 ha.
Strict new clearing between composites = 186 ha (0.3% of AOI); 553 ha including ambiguous 2022 and 2024.
Day 6 upper bound 886 ha is 1.6x the generous and 4.8x the strict Hansen figure; spatial overlap not yet tested.
Hansen gain (2000-2012): 557 ha.
WorldCover tree 2020 -> 2021: IoU 0.795; +2,062 ha net (algorithm versions differ, not real change).
NDVI-forest (composite A, 0.616) = 22,491 ha (36%) vs single-scene 17,486 ha (Day 5): same threshold, different input.
  vs Hansen end-2021: precision 0.42, recall 0.76, IoU 0.374.  vs WorldCover 2021: precision 0.61, recall 0.88, IoU 0.566

## Observations
- Loss pattern: large compact blocks in 2001-2006 (upper centre-right), scattered small patches since 2010.
- WorldCover-only areas include a large block whose Hansen history shows early loss (2001-2006):
  consistent with regrowth or plantation after 2000 (to confirm in QGIS).
- Hansen-only areas are scattered speckle and a thin line along the river.
- NDVI-forest includes many thin stream strips and small blobs that neither label calls forest.

## Limits
- Weak labels: 30 m, Landsat-based, loss includes fire and logging.
- Hansen 30 m resampled to 10 m is blocky and may be offset by up to ~15 m.
- 2022 and 2024 loss years are ambiguous relative to our June-July composites.
- WorldCover 2020 and 2021 are not comparable as change.

## Decisions
- Canopy >= 30% kept. NDVI threshold 0.616 unchanged (baseline only).
- Day 12 label rule: forest = Hansen AND WorldCover tree; non-forest = neither; ignore (255) otherwise,
  plus Hansen gain and ambiguous loss years (2022 for A, 2024 for B).
- Day 13 hand-labelled set to be stratified over agreement and disagreement classes.
- AOI kept; add a second, more actively clearing AOI is a Day 15 decision (186 ha of strict positives is thin).

## Next
Day 12: align labels to the master grid, build label_A and label_B with ignore values.