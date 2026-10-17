composite_a: smoother than the single scene; [no ghosts ].
count_a: mostly high count looks; low-count areas are rivers mainly(blobs / rings / river / edge).

python src/cache_dates.py --period a --limit 1
>> python src/cache_dates.py --period a
period_a: 1 dates selected (AOT <= 0.13):
  ['2022-06-04']
[1/1] 2022-06-04  baseline 05.10  shape (4, 2501, 2501)  valid 100.0%  37 s

Cached to: C:\Users\deept\Desktop\Deforestation Project\deforestation\data\cache
period_a: 9 dates selected (AOT <= 0.13):
  ['2022-06-04', '2022-06-19', '2022-06-24', '2022-06-29', '2022-07-04', '2022-07-09', '2022-07-14', '2022-07-19', '2022-07-24']
[1/9] 2022-06-04  already cached, skipping
[2/9] 2022-06-19  baseline 04.00  shape (4, 2501, 2501)  valid 100.0%  31 s
[3/9] 2022-06-24  baseline 05.10  shape (4, 2501, 2501)  valid 100.0%  35 s
[4/9] 2022-06-29  baseline 04.00  shape (4, 2501, 2501)  valid 100.0%  27 s
[5/9] 2022-07-04  baseline 05.10  shape (4, 2501, 2501)  valid 100.0%  32 s
[6/9] 2022-07-09  baseline 04.00  shape (4, 2501, 2501)  valid 100.0%  26 s
[7/9] 2022-07-14  baseline 05.10  shape (4, 2501, 2501)  valid 100.0%  33 s
[8/9] 2022-07-19  baseline 05.10  shape (4, 2501, 2501)  valid 100.0%  32 s
[9/9] 2022-07-24  baseline 05.10  shape (4, 2501, 2501)  valid 100.0%  34 s

Cached to: C:\Users\deept\Desktop\Deforestation Project\deforestation\data\cache
(deforest) PS C:\Users\deept\DESKTOP\Deforestation Project\deforestation> python src/composite.py --period a
period_a: compositing 9 dates, min_clear_obs = 3

date         good%   NDVI median   forest%
2022-06-04    99.6       0.623     52.19
2022-06-19    99.2       0.636     57.37
2022-06-24    99.5       0.598     43.56
2022-06-29    99.7       0.598     44.51
2022-07-04     4.2       0.536     32.24
2022-07-09    99.7       0.498     28.05
2022-07-14    95.0       0.474     26.10
2022-07-19    99.6       0.453     25.09
2022-07-24    26.7       0.413     23.02

Good observations per pixel
  0 looks:   0.14%
  1 looks:   0.07%
  2 looks:   0.06%
  3 looks:   0.11%
  4 looks:   0.08%
  5 looks:   0.08%
  6 looks:   3.13%
  7 looks:  71.48%
  8 looks:  20.80%
  9 looks:   4.06%
  mean 7.23, median 7
  pixels below min_clear_obs (3): 0.265%  (set to NaN)

Composite reflectance (valid pixels)
  B02: median 0.0444  p1 0.0151  p99 0.0677
  B03: median 0.0718  p1 0.0280  p99 0.1040
  B04: median 0.0730  p1 0.0163  p99 0.1358
  B08: median 0.2633  p1 0.1680  p99 0.3668

Saved: C:\Users\deept\Desktop\Deforestation Project\deforestation\data\composites\composite_a.tif
Saved: C:\Users\deept\Desktop\Deforestation Project\deforestation\data\composites\count_a.tif
(deforest) PS C:\Users\deept\DESKTOP\Deforestation Project\deforestation> python src/composite_check.py
NDVI percentiles          p2     p25  median     p75     p98
  composite            0.343   0.495   0.566   0.684   0.879
  2022-07-09           0.301   0.427   0.498   0.647   0.881

Forest share (NDVI above threshold)
  threshold 0.616: composite 36.05%   2022-07-09 28.05%
  threshold 0.720: composite 21.33%   2022-07-09 19.68%
  Otsu on the composite: 0.649   (single scene, Day 5: 0.616)

Composite - 2022-07-09 NDVI: median +0.044, robust sigma 0.048, share |d| > 0.1: 12.83%

Split-half test
  half 1: ['2022-06-04', '2022-06-24', '2022-07-04', '2022-07-14', '2022-07-24']
  half 2: ['2022-06-19', '2022-06-29', '2022-07-09', '2022-07-19']
  pixels with >= 2 looks in both halves: 99.54%
  NDVI difference: median +0.007, robust sigma 0.039, share |d| > 0.1: 2.30%
  For comparison, single dates 10 days apart (Day 6): median -0.028, sigma 0.032

Saved figure: C:\Users\deept\Desktop\Deforestation Project\deforestation\outputs\day9_composite_check.png