# Day 10 notes: 2024 composite and alignment

## Setup
Same recipe as 2022: window 2024-06-01..07-31, AOT <= 0.13, SCL [4,5,6], 5 px dilation, min_clear_obs 3.
Dates used (11): 2024-06-03, 06-08, 06-13, 06-18, 06-23, 06-28, 07-03, 07-08, 07-13, 07-18, 07-23 [confirm].
2024-07-28 excluded (AOT 0.170).
Not identical: 9 dates in 2022 vs 11 in 2024, different cloud patterns, different date mix.

## Count map (2024)
Mean __ looks of 11. Pixels below 3 looks: __%. Low-count areas: __.

## Alignment (align_check.py)
All PASS: yes. Phase-correlation shift: __, __ px. Valid in both: __%.

## Change between composites (composite_compare.py)
dNDVI all pixels: median __, sigma __ (Day 6 single dates: -0.066 / 0.074; null -0.028 / 0.032).
dNDVI forest at A: median __, sigma __ (Day 6: -0.035 / 0.044).
Band shifts: B02 __, B03 __, B04 __, B08 __ (Day 6: +0.011, +0.009, +0.019, +0.007).
By class: forest in both __, non-forest in both __, forest->non-forest __.
Decreases vs increases at 0.25: __ ha vs __ ha (Day 6: 2,019 vs 75).
Refined flags: __ ha after MMU (Day 6: 886 ha); __% sit on pixels with < 5 looks in 2024.
Split-half sigma: 2022 __, 2024 __. Cross-year sigma __.
Reading: [composites reduce noise but a systematic shift remains | shift also reduced | no improvement].

## QGIS
composite_b vs composite_a: no sideways shift; large-scale tone gradient [still there / gone].
count_b: __.

## Limits
- Flags are still an upper bound: forest at A uses 0.616 and no labels exist yet.
- A uniform shift cannot be separated into atmosphere, drying and real change with this data.
- Nothing was tuned from today's numbers.

## Next
Day 11: choose a label source and forest definition; download labels for the AOI.