# Day 8 notes: lazy stack, deduplication, cloud mask

## Master grid
Snapped outward to 10 m multiples: shape (2501, 2501), origin (569630, 8879360).
Legacy Day 4-7 files sit at row 1, col 0 of this grid. verify_stack.py: bands identical,
SCL agreement __%. New grid covers 100% of the AOI.

## Deduplication
2022: __ items -> __ unique dates (__ duplicates). 2024: __ items -> __ dates.

## Lazy loading
Stack builds in __ s, nothing downloaded. Full stack would be __ GB.
A 256x256 window across __ dates loaded __ MB in __ s.

## Scene quality (scene_quality.py)
AOT range: 2022 __-__, 2024 __-__. Gap in AOT values: [yes at __ / no].
Cutoff chosen: __ (reason: __). Usable dates: 2022 __ of __, 2024 __ of __.
Usable per month: __.
Scene-level vs AOI-level cloud differ on: __.
Cross-check: 2022-07-09 AOT __ (Day 7: 0.064), 2024-08-02 AOT __ (Day 7: 0.477).

## Cloud mask (cloud_mask.py, dates __)
Blue vs distance: __x at 1-2 px, __x at 5-10 px, __x by __ px.
Classes 2 and 7 within 10 px of cloud: __% and __% (class 4: __%).
Dilation chosen: __ px (reason: __). Retained: __% of valid pixels on __.
Shadows missed: [yes/no], seen at __.

## Open items
- Day 9: build the 2022 composite from usable dates, with the mask above
- Check that enough clear observations exist per pixel (count map)
- 2024 still shows redder surface even on clean dates (Day 7): not yet explained

   Dedup: 2022 34 -> 19 dates (15 duplicates; kept 15 at 05.10, 4 at 04.00). 2024 21 -> 21 (10 at 05.10, 11 at 05.11).
   Grid (2501, 2501), origin (569630, 8879360). verify_stack: bands identical, SCL 100%, covers AOI.
   Lazy stack builds in 1.0 s; full stack 5.00 GB (float32); 256x256 window x 40 dates = 10.5 MB in 78 s.
   AOT matches Day 7 on every date compared. AOT is coarse (0.316 on 4 dates, 1.155 on 2) and
   underestimates thick smoke (2022-09-02: AOT 0.316 but blue_p1 0.122). No natural gap.
   Aug-Sep unusable in both years. Chosen: window Jun 1 - Jul 31, scene_aot_max 0.13 (drops 2022-07-29
   and 2024-07-28 symmetrically). Judgment call, not outcome-driven.
   Scene-level cloud misleads: 2022-07-04 tile 22.4% vs AOI 95.4%; 2022-06-04 tile 20.3% vs AOI 0.0%.
   Dilation 5 px (provisional, see cloud mask section).
   Baseline 04.00 vs 05.10 pair test (3 dates): NDVI shift ≤0.0011, sigma ≤0.006. Negligible