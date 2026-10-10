# Day 5 notes: NDVI baseline (scene 2022-07-09, tile 20LNP)

## 1. Threshold
Otsu gave 0.616, and I used 0.616 for the baseline map. The NDVI histogram has
a large bump at ~0.45 (pasture/soil) and a smaller bump at ~0.86 (forest).
The valley is at ~0.72-0.76, so Otsu is NOT in the valley: it sits on the
shoulder of the pasture bump, pulled left by the large, broad pasture class.
The sweep confirms this. Forest area changes by only ~2,000 ha per 0.05 step
between 0.70 and 0.80, but by 3,200-4,750 ha per step around 0.55-0.65.
Moving from 0.55 to 0.65 changes forest area by 7,954 ha (about 34%), so the
map is sensitive to this choice. The ambiguous NDVI range is ~0.62-0.75.

## 2. Forest area
17,486 ha = 28.0% of 62,500 ha valid area (threshold 0.616).
At 0.75 it would be ~11,138 ha (17.8%). This is "forest-like greenness",
not verified forest: there are no independent labels yet.
21,425 patches, of which 7,148 are single pixels and 19,913 (93%) are below
0.5 ha. Largest patch 1,732 ha, median patch 0.03 ha.
58.7% of forest area is in patches >= 100 ha; 16.4% is in patches < 5 ha.
SCL class 4 ("vegetation") covers 86.4% of the AOI and 65.5% of it has
NDVI < 0.6, so SCL is not a forest mask.

## 3. Failures observed
- Speckle and ragged outlines: many tiny yellow contours in the pasture areas
  of the zoom panel; these are the sub-0.5 ha patches an MMU would remove.
- Stream and riparian strips: a branching network of narrow green strips is
  mapped as forest. Could be real riparian forest or wet green pasture. (verify)
- Bright pink-red patches next to the dark crimson forest in the zoom panel
  are probably dense or wet pasture with high NIR, included at 0.616. (verify)
- Mixed pixels at edges: forest/pasture boundaries are ragged at 10 m.
- A darker maroon patch in the upper centre of the false-color panel has
  lower, patchy NDVI. It could be degraded forest, a burn scar, or a crop.
  A single threshold treats it arbitrarily. (verify)
- Correct: the river is excluded (water/low NDVI) and the town at the left
  edge appears as non-forest. (verify)

## 4. What NDVI can't do
- One number per pixel and no spatial context: it cannot use canopy texture
  or shape (straight field edges vs irregular forest), so it speckles.
- A single fixed cutoff in a continuous gradient: no threshold cleanly
  separates dense pasture, wet vegetation and forest (0.62-0.75).
- B08 (NIR) barely separates the classes in the dry season (d-prime 0.65);
  a model can combine blue, green, red and SWIR rather than depending on a ratio.
- Single date: haze, shadows and phenology shift NDVI and move the threshold.

## 5. Check: threshold 0.72 vs 0.616
Raising the threshold from 0.616 to 0.72 reduced forest from 17,486 ha (28.0%)
to 12,263 ha (19.6%): a 30% drop (-5,223 ha) for a 0.1 NDVI change.
The largest patch fell from 1,732 ha to 775 ha, so the large patch at 0.616
was partly a connectivity artifact (narrow strips linking blocks).
Median patch size stayed 0.03 ha and the small-patch share was unchanged:
raising the threshold does not remove speckle; an MMU or a model with spatial
context is needed. At 0.72 the thin stream strips and pink forest fringes
disappear, but holes appear inside large forest blocks. Both versions look
plausible, so the threshold cannot be chosen without independent labels.
Baseline kept at 0.616 (Otsu) and documented as such. The 0.72 value is a
sensitivity check, not a tuned result.