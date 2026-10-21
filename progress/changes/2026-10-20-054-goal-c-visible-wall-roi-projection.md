# GOAL C visible wall ROI and voxel-side diagnostic #298

Related dialogue: [2026-10-20-054](../../collaboration/dialogues/2026-10-20-054-goal-c-visible-wall-roi-projection.md)

## Change

- Added an offline analyzer and compact evidence report for the matched-layout snapshot runs #295 and #296. It projects the analytic calibration wall through the D435i frustum at each `last_fused_depth_source_stamp_ns`, selects wall-assigned occupied centers in that per-snapshot frustum ROI, and maps their centers back through each run's existing single SE(3) alignment.
- Both epochs select map-frame x centers `3.05 → 2.95 → 3.05 m` across the three snapshots. In #296, all 72 first-snapshot wall SDF outliers map back to `x=2.95 m`; the full-run alignment shifts x by a median −54.5 mm (P05/P95 −61.2/−50.4 mm), yielding 104.5/111.2 mm median/P95 SDF distances. This makes one-cell quantization combined with alignment a plausible explanation, not a proven cause.
- GOAL C remains pending. No milestone status changed.

## Verification

- `python3 -m py_compile artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/analyze_visible_wall_roi.py` — passed.
- `python3 artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/analyze_visible_wall_roi.py` — passed and regenerated the report.
- The analysis verified SHA-256 for all 25 captured source inputs. Compact evidence: [#298](../evidence/p2-visible-wall-roi-projection-20261020-298.json); detailed spatial output: `artifacts/runs/p2-map-voxel-snapshot-service-20261020-296/visible-wall-roi-analysis.json`.

## Limitations and next step

- The projected ROI is frustum-based, not an occlusion-aware depth-return mask; the snapshots have no per-voxel observation timestamps. A logged pose projection opportunity does not prove which image produced an occupied cell.
- The alignment was fitted to the short trajectory and is not an independent map calibration. Its small rotation can shift points on the distant wall by several centimetres. The 0.10 m SDF cutoff equals one voxel width and is exploratory.
- Next, use a matched repeat with the wall face displaced from the nominal x-grid boundary, or an independently calibrated map-to-world transform, to separate map-cell side selection from alignment and depth error. Freeze coverage/ghosting criteria only after that comparison.
