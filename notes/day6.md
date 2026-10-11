# Day 6 notes: NDVI differencing baseline (A = 2022-07-09, B = 2024-07-13)

## 1. Smoke check
2024-07-13 vs 2022-07-09: blue median x1.27, dark floor x1.63, AOT x1.28
(0.064 -> 0.082). Natural 2022 variation (07-19 vs 07-09): x1.05, x1.06, x1.00.
2024 is outside natural variation, but absolute AOT is low (clear air) and the
AOT layer is nearly uniform (median = p95), so it cannot show local plumes.
NIR rose slightly (+0.0074), so this looks like drier/browner surface plus a
small aerosol effect rather than pure haze. Decision: keep the scene for the
baseline; treat 2024 differences with caution.
Second 2024 date (2024-07-18): not done.

## 2. Global shift and noise
Null (07-09 vs 07-19): median dNDVI -0.028, sigma 0.032 (forest at A: -0.008, 0.023).
Real (2022 vs 2024):   median dNDVI -0.066, sigma 0.074 (forest at A: -0.035, 0.044).
Real run has 2.3x the noise and 2.4x the shift. A -0.25 cut is 2.5 sigma
from the median in the real run vs 6.9 sigma in the null.

## 3. Flagged area after MMU (0.5 ha)
Null,  drop 0.25: naive 7 ha, refined 5 ha (4 patches)  <- noise floor
Real,  drop 0.25: naive 1,469 ha (559 patches), refined 886 ha (369 patches), 5.08% of forest at A
Real,  drop 0.40: naive 153 ha (71), refined 148 ha (68), 0.84% of forest at A
MMU kept 67% of refined area in the real run vs 31% in the null.

## 4. Symmetry
Decrease/increase at 0.25: null 4.8 (21 vs 4 ha), real 26.8 (2,019 vs 75 ha).
A one-sided ratio fits both deforestation and a year-wide darkening/drying,
so it is not evidence of clearing by itself.

## 5. Patch inspection (flag_patches.py, drop 0.25)
369 patches, 886 ha, median 1.15 ha, largest 33.0 ha.
NDVI at A of flagged patches p10/p25/p50/p75/p90: 0.652 / 0.674 / 0.721 / 0.774 / 0.818.
38.5% of flagged area had NDVI_A below 0.72 (ambiguous zone from Day 5).
NDVI at B is mostly 0.33-0.48, the pasture range, not bare soil.

Manual QGIS tally (10 random patches: 31, 81, 263, 245, 174, 97, 90, 143, 182, 309):
real clearing __, pasture/crop change __, edge/mixed __, shadow/wet/burn __, unclear __.
5 largest (211, 191, 114, 318, 161): __
Caveat: 10 patches is a rough sample, and patch counts are not hectares.

## 6. Why this baseline is not enough
- Real-run shift and noise are 2-2.4x the null: a fixed threshold cannot absorb
  a systematic year-to-year offset.
- "Forest at A" at 0.616 includes dense green pasture, so flags include pasture
  drying. 886 ha is an upper bound, not a deforestation estimate.
- The null experiment underestimates the two-year problem (no phenology or year effects).
- Fixes ahead: median composites (Days 8-10), independent labels (Days 11-13),
  a model using texture and context (Days 15-21).
- Bug found: output filenames ignored --drop, so the strict run overwrote the main
  one. Fixed by adding the threshold to the filename.