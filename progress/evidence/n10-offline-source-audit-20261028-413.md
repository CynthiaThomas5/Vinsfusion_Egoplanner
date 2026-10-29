# N10.3 offline source and evidence audit — #413

## Scope

Read-only review of the #404/#411/#412 calibration archives, PX4 source-lock chain, same-epoch VIO/yaw/RPE, raw map voxel behavior, and #412 resource/queue evidence. No flight, runtime change, acceptance-threshold change, or control decision was made.

Machine-readable replay: [`n10-offline-source-audit.json`](../../artifacts/runs/n10-20261028-413-offline-source-audit/n10-offline-source-audit.json), SHA-256 `382a971d5e05b3a44147d8f3e1fb75c7e8573181974ccf040bae2b5074690931`. Reproduction entry point: [`analyze_n10_offline_source_audit.py`](../../artifacts/runs/n10-20261028-413-offline-source-audit/analyze_n10_offline_source_audit.py).

## Findings

### Source identity and continuous clearance

The host PX4 checkout is clean at locked commit `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`; its Gazebo submodule is `b6127f4ec20de867e215fb5f78ae88b80f371909`. Current airframe SDF, motor plugin, and ESC bridge match those locked source files.

The run contracts do not have equal identity strength. #404 records a dependency-lock hash beginning `4ec471…`, and #411 records `9f6967…`; the current lock and #412 contract both record `506bac…`. The PX4 files match the current lock, but #404/#411 do not bind that exact lock, so their host interval replay remains `INSUFFICIENT_MODEL_IDENTITY` despite computed positive minima of 0.16276 m and 0.25482 m. #412 binds the lock and passes all 19 model/source/contact identity checks; its 27,461 no-contact intervals have a positive lower bound, minimum 0.41054 m. Skid-contact intervals are evaluated separately, with zero prohibited contact. Preserve the weaker runs as diagnostics, not qualified continuous-clearance evidence.

### VIO, yaw, and relative motion

Each run was replayed separately in its own epoch using the same scale-one prestream alignment and source-time 1/5/10 s RPE method. The goal-motion 10 s translation RPE P95 was 0.03856 m for #404, 0.26859 m for #411, and 0.26348 m for #412. Truth yaw total variation was 53.28°, 750.82°, and 670.42°, respectively. The high-yaw runs had larger relative translation drift; the 1 s heading lookahead in #412 reduced absolute position P95 from #411's 0.469 m to 0.164 m but changed RPE P95 little.

An additional within-run grouping of overlapping 10 s RPE windows by maximum truth yaw rate shows the same descriptive pattern in #412: windows at or below 0.10 rad/s have translation RPE P95 0.0505 m (294 windows), while windows above 0.50 rad/s have P95 0.2819 m (279 windows). The intermediate bins are not monotonic, and #411/#412 are not paired trials. This supports testing whether a yaw-rate cap affects drift; it does not establish causality or justify changing a threshold.

### Raw map and resource evidence

Of #412's 39 fully-contained known-free voxels, 35 are nearest the truth box's positive-Y face and 4 the negative-X face. Their nearest interior margins are 0.000562–0.001391 m in a 0.1 m voxel map. The source code confirms per-frame hit/miss voting; ties select occupied, traversal excludes the endpoint voxel, and the persisted snapshot has no per-voxel vote history. The #412 run-local injector sampled only every tenth occupancy cloud and recorded box ROI points from injection −0.5 s through +5 s. If that subset had no ROI point, it scheduled the fallback snapshot at +8 s. Therefore `no_roi_cloud_observed` means no ROI point appeared in the sparse, limited sample before the snapshot; it does not establish that no ROI cloud or voxel update existed. The snapshot also has no per-voxel vote history. Boundary ray/endpoint interaction remains unproven; raw-map classification stays `FAIL` against the unchanged diagnostic candidate. #414 will observe every cloud through watermark freeze and record targeted per-voxel updates.

The 184.27 s #412 workload produced 183 one-second resource samples, RTF min/median/P95/max of 0.516/0.890/0.918/1.172, 3.247 GiB container memory peak, and no sampled OOM kill or CPU throttling. Mapping depth pending reached its configured 8/8 queue and recorded 26 depth and 21 keyframe drops. VINS acc/gyr current queue lengths during the goal were P50/P95/max 28/29/30 and process high-water 90; feature current length was 1 and high-water 2. VINS source declares no finite queue capacity. These measurements support a partial platform/load description, not a 600 s capacity or growth limit. Do not invent a runtime rejection threshold; N16 remains the post-freeze long-duration qualification.

## Decision and next experiment

Retain #404/#411 metrics as diagnostics and retain only #412 as identity-qualified continuous-clearance evidence. Do not merge runs or infer a common runtime identity. Preserve all thresholds and failure/inadequate statuses.

The next normal-flight experiment should hold the route, 0.40 m/s planner setting, one-second heading lookahead, obstacle timing, sensor/model, and recording fixed while changing only the EGO yaw-rate cap. The offline association motivates this variable, but does not predict success. Keep the independent 3 s position/yaw arrival requirement and existing VIO candidates unchanged. Failure to reach the goal or improve the error budget remains a failure and triggers implementation diagnosis; it does not authorize deleting the metric. In the same run, improve read-only map evidence so post-injection ROI source coverage and per-voxel update contributions can be attributed without adding an online gate.

The other four missing calibration classes remain stereo stream loss, camera-IMU stream loss, VINS restart, and simulation clock rollback. They remain separate current-version natural-terminal calibrations; they do not count as N15 repeats. N10 remains `in_progress`; N10.4 criteria, N10.5 clean rebuild, N10.6 rebuilt regression, and N10.7 freeze remain open.
