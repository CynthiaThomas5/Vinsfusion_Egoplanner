# N10 integrated calibration result — #412

## Scope and identity

This is one diagnostic calibration, not a formal N11–N16 result. The run used the 16 m `speed040` EGO route with the one-second path-heading lookahead, a 20 simulated-second post-goal hold, and one static 0.8 × 0.8 × 2.8 m box inserted 12.004 simulated seconds after goal start. It captured source-timed VIO/truth, 4 ms Gazebo states, body clearance/contact, raw and inflated occupancy snapshots, selected depth frames, replan events, sensor receipt-to-MCAP integrity, resource samples, and VINS estimator queue telemetry.

- Run: `n10-20261028-412-speed040-yaw-lookahead-calibration`
- Runtime contract SHA-256: `0bf84419cc3f81d1cf22645f56e74358e60bbc74c1dbe09793900d81733057f2`
- Goal / epoch / map: `72d50119d40343f8932799e563c4bae3` / `0b4b77dc9f8147119b68383999093457` / `0b4b77dc9f8147119b68383999093457-2e6f0d8d36594efb82c1cf4d100fa797`
- Protocol and prelaunch records: [protocol](n10-integrated-calibration-protocol-20261028-412.json), [prelaunch](n10-integrated-calibration-prelaunch-20261028-412.json)
- Raw run directory: `artifacts/runs/n10-20261028-412-speed040-yaw-lookahead-calibration/`

## Findings

| Measure | #412 observation | Candidate comparison / result |
| --- | --- | --- |
| Native action and independent arrival | Action succeeded at `[15.95517, -0.00212, 0.99343]`; independent joint position/yaw dwell was 3.056 sim s, with max position error 0.29987 m and yaw error 0.18186 rad | Arrival contract PASS (3.0 sim s; 0.30 m; 15°) |
| Raw VIO absolute error | Goal-motion position P95/max 0.1640/0.2359 m; absolute yaw P95/max 0.3927/0.7208° | Within revision-3 provisional absolute-error values; one run does not establish general qualification |
| Raw VIO 10 s RPE | Goal-motion translation P95 0.2635 m; rotation P95 0.1789°. Active-hold translation/rotation P95 0.0158 m/0.1302° | Translation FAIL against the 0.05 m draft candidate; rotation within 0.5° candidate |
| VINS velocity error | Goal-motion P95 0.0474 m/s, maximum 0.3364 m/s; active-hold P95/max 0.00587/0.00782 m/s | Goal-motion maximum FAIL against 0.1 m/s candidate; retain the transient in the data |
| Map source/update age | Maximum 0.164/0.120 sim s | Within 0.2 sim s provisional offline values; no runtime gate |
| Full-body clearance and contact | Every 4 ms solver state captured; minimum discrete clearance 0.42351 m; prohibited contact count 0. The no-contact dynamics-bound lower value was 0.41054 m across 27,461 intervals | Discrete and interval SITL clearance PASS under the declared model assumptions; a host replay confirmed all PX4/Gazebo/model/plugin identities against the lock. The original container evaluation reported insufficient identity because it did not have usable VCS metadata; its original file is preserved alongside the host replay |
| Tracking relation | 9,865/9,865 READY commands paired to truth; error P95/max 0.41468/0.49011 m. Scalar translation-only bound was nonnegative for all samples; minimum 0.01439 m | Diagnostic only. The candidate scalar tracking limit is still unqualified; the minimum bound leaves little margin and does not cover attitude, map, dynamics or model uncertainty |
| Raw map classification | In the post-injection box ROI, 39 fully contained known-free voxels: 35 nearest the positive-Y face and 4 nearest the negative-X face. Their nearest voxel interior is 0.000562–0.001391 m from a truth-box face. Inflated occupancy covered all 1,792 ROI cells | FAIL against the unchanged zero-known-free diagnostic candidate; cause remains unknown: the observer sampled every tenth occupancy cloud only through injection +5 s, while the fallback snapshot was scheduled at +8 s; `no_roi_cloud_observed` does not prove that no ROI cloud/update existed. No per-voxel update history was recorded |
| Raw surface support | Observed occupied support on three faces; maximum occupied-cell-center error 0.06359 m. Three other faces were unobserved | INSUFFICIENT for all-face geometry; optional point-query service was unavailable |
| Dynamic obstacle/replan | Gazebo create request was acknowledged in 0.119 wall s; a replacement trajectory ID and actual route were recorded; no prohibited contact | INSUFFICIENT to link the replan to a source-covered raw/inflated map transition and to qualify its timing/clearance as one causal chain |
| Resource/queues | 184.27 wall s, 183 one-second samples, RTF min/median/P95/max 0.516/0.890/0.918/1.172; container memory peak 3.25 GiB; no sampled cgroup OOM kill or CPU throttling. Mapping pending-depth high-water reached 8/8; 26 depth and 21 keyframe drops. VINS acc/gyr reported high-water 90, feature 2; source does not declare queue capacity | Useful representative-load measurement, but capacity/freshness rationale and multi-minute growth behavior remain unresolved; do not infer a hard limit or add runtime refusal |
| Sensor recorder and terminal state | Receipt-to-MCAP evaluator PASS; native action completed, then bridge/PX4 independently read LANDED, disarmed, control-disabled and zero control. `safe-to-stop.json` says safe | Capture integrity and normal mission closeout PASS; not a fault calibration |

The bridge history retains the text `px4_preflight_failed` in an early disabled sample. It does not describe the #412 takeoff or mission result: the recorded preflight and takeoff admission passed, the action succeeded, and the final independent state was safely landed/disarmed. Keep the historical string in the archive; do not classify it as an active fault.

A later source audit found that the #412 obstacle-cloud observer sampled every tenth callback and stopped its ROI window at injection +5 s, but used a no-ROI fallback snapshot at +8 s. Thus `no_roi_cloud_observed` is a coverage-limited negative observation, not proof that no ROI cloud or voxel update existed. #414 will extend read-only coverage through snapshot watermark freeze and add a targeted per-voxel update trace.

The VIO evidence points to a real split between absolute and relative error: absolute error improved from the earlier yaw-follow run, while 10 s translation RPE remained high. The observed run does not isolate whether yaw dynamics, visual coverage, trajectory curvature, or the obstacle-triggered segment caused the excess. The raw-free cells are similarly not yet attributed to a mapper defect: they lie near the positive-Y and negative-X faces, but the available records cannot identify which depth/ray updates assigned those cells. Neither gap is resolved by changing a threshold.

## Offline evaluator correction

The first interval-clearance report, `n10-interval-clearance-bound.json`, was generated under `/workspace` and returned `INSUFFICIENT_MODEL_IDENTITY` because that evaluator could not read the Git source identity. I reran the same evaluator against the same raw run and the locked host checkout, writing a separate [host replay](../../artifacts/runs/n10-20261028-412-speed040-yaw-lookahead-calibration/n10-interval-clearance-bound-host-replay.json). All 19 model/contact/source identity checks pass; the run contract's `dependencies/sources.json` hash matches the host lock, and PX4 commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`, Gazebo submodule `b6127f4ec20de867e215fb5f78ae88b80f371909`, airframe SDF and motor/ESC files match. Every one of 27,461 airborne intervals has a positive bound; minimum 0.41054 m. The 810 skid-contact intervals remain separated and the independent contact report shows zero prohibited contact. The initial report is preserved for provenance; the host replay is the corrected identity-qualified analysis.

## Status and next actions

Overall acceptance remains `INSUFFICIENT`. #412 closes the #409 combined-calibration attempt and adds queue/load observations, but does not close N10.3. The next work is offline first: (1) audit the locked-versus-actual PX4/SDF/plugin source differences; (2) correlate #404/#411/#412 VIO and yaw/command trajectories without merging epochs; (3) inspect raw map ray-clearing/voxel-boundary semantics against the archived depth and snapshot evidence; (4) turn the resource and fault observations into source-backed candidate limits only where the data support them. If an unresolved item needs another run, record the single variable and the missing measurement before launch.

N15's six fault classes × two formal repeats and N16's continuous 600 simulated seconds remain post-freeze work. #412 is not credited toward either.
