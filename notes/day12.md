# Day 12 notes: aligned labels

## Rules (stored in each file's tags)
label A (Jun-Jul 2022): forest = Hansen (canopy>=30% in 2000, land, no loss through 2021) AND WorldCover 2021 tree.
label B (Jun-Jul 2024): same with loss through 2023; WorldCover 2021 carried forward by removing Hansen loss 22-23.
Non-forest = neither source says forest. Ignore (255): Hansen gain, no-data, ambiguous loss year (22 for A, 24 for B),
and any disagreement between sources.
change: 1 = forest at A and non-forest at B (loss 2023 only), 0 = forest at both, 255 otherwise.
Resampling: nearest from EPSG:4326 (Hansen ~28 m, WorldCover 10 m) to the 10 m UTM master grid.

## Results (build_labels.py)
Checks passed (values 0/1/255, no non-forest(A) -> forest(B), positives = loss 2023 on label-A forest).
Hansen end-2021 forest 12,617 ha (matches Day 11).
label A: forest 8,590 ha, non-forest 42,893, ignore 11,067 (17.7%).
label B: forest 8,340 ha, non-forest 43,434, ignore 10,776 (17.2%).
Ignore reasons (A / B, ha): Hansen gain/no-data 557 / 557; ambiguous loss year 291 / 71;
Hansen-only 3,648 / 3,643; WorldCover-only 6,572 / 6,505.
Change: stable forest 8,340 ha, clearing 181 ha in 321 patches (median 0.18 ha, largest 22.4 ha);
78% of clearing area (~141 ha) is in patches >= 0.5 ha. Day 11 Hansen loss 2023: 186 ha.
Cross-checks: 8,590 = 8,340 + 181 + ~69 ha ignored at B (loss 2024).

## Checks (label_check.py)
Grid/metadata: all PASS (origin 569630, 8879360).
Registration vs composite-A NDVI forest, +-3 px: Hansen best (+3,+2) at the window edge, IoU 0.378 -> 0.406,
no interior peak (inconclusive); WorldCover best (-1,-1), IoU 0.563 -> 0.569 (<= 1 px);
agreement label A best (0,0), IoU 0.510. Extended +-8 px test: __.
d-prime on independent labels (forest vs non-forest, composite A): B02 3.27, B03 3.15, B04 3.13, B08 0.26, NDVI 3.10
(Day 5 circular: 2.90 / 2.29 / 3.17 / 0.65). Blue alone matches NDVI; NIR is nearly uninformative in the dry season.
NDVI forest (0.616) on confident label-A pixels: precision 0.521, recall 0.959, IoU 0.510.
About 7,554 ha (17.6%) of confident non-forest exceeds 0.616; forest p5 0.637 vs non-forest p95 0.693 (classes overlap).
6,729 ha of the 22,491 ha NDVI-forest falls on ignored label pixels.

## QGIS
Edges / blocks: __. Blue block (WorldCover-only): [ignored, looks like __].
Clearing patches inspected (__): real clearing __, regrowth/pasture __, unclear __.


## Limits
- Weak labels from two products; both can share errors.
- label_change covers only clearing of old forest both sources call forest, and has no values on non-forest at A.
  Day 26 must score flags on label-A non-forest as false positives.
- Usable positives are about 141 ha (patches >= 0.5 ha), so change precision/recall will be uncertain.
- WorldCover-only (6,572 ha) is ignored: probably regrowth blocks plus narrow riparian strips Hansen cannot resolve.
- d-prime is for confident pixels only; real separability on the ignored 18% is lower.
- Hansen registration unresolved (see shift test); no correction applied.

Registration (shift test, +-8 px; best shift (dr, dc) = Hansen at (r, c) matches imagery at (r+dr, c+dc)):
Hansen vs WorldCover 2021: IoU 0.464 -> 0.525 at (4, 3), gain +0.061, interior peak.
Hansen vs NDVI forest: IoU 0.378 -> 0.405 at (4, 2), gain +0.027, interior peak.
WorldCover vs NDVI forest: 0.563 -> 0.568 at (-1, -1), gain +0.005 (aligned).
Pre-registered rule (interior peak, both gains >= 0.03, best shifts within 1 px): FAILED on one gain (0.027 < 0.03).
Evidence leans toward Hansen being displaced ~30-40 m (about 4 rows, 2-3 cols) from Sentinel-2; cause unknown.
Impact: mild for labels A and B (offset edges become ignore); serious for label_change (positives are Hansen-only,
median patch 0.18 ha).
Follow-up direct test (Hansen 2023 loss vs composite dNDVI, control = 2018 loss): result __.
Decision: [labels left unshifted / hansen_shift_px set to [__, __]].

## Next
Day 13: stratified hand-labelled reference set (agreement and disagreement classes) in QGIS.