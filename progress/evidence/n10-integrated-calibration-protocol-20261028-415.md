# N10.3 #415 compact voxel trace calibration

## Purpose

Measure whether compact serialization reduces the read-only per-voxel trace volume under the same mapping and flight load as #414. This is a calibration run, not N15/N16 qualification.

## Single changed variable

Patch 0059 changes the trace row encoding from v1 JSON objects to v2 compact arrays. The ROI remains exactly `[0.6, 0.6, 1.6] m`; route, speed040 profile, 0.10 rad/s EGO yaw-rate cap, spawn, target, obstacle geometry and timing, sensor streams, contact model, collision behavior, observer set, and acceptance thresholds are held fixed from #414.

Each compact row preserves voxel indices, hit/miss vote counts, pre/post log odds, and pre/post occupancy class codes. The trace is read-only and has no control subscriber. Observer errors or metrics cannot add takeoff refusal, cancellation, or landing behavior.

## Comparison and interpretation

Compare trace bytes and update counts, mapping queue drops, CPU/RSS/RTF, map source coverage/classification, replan, tracking/VIO, full-body interval clearance, prohibited contact, action completion, and native terminal state against #414. A lower trace volume does not prove it caused a better flight result; if #415 still fails, restore the yaw cap in a separately isolated next run before attributing the failure. No thresholds are changed and calibration results do not count toward N15/N16.

## Inputs

- Run: `n10-20261028-415-speed040-yawcap010-compacttrace-calibration`
- Planner: `config/components/mapping/n10_horizon5_speed040_yawcap010_compacttrace_calibration.json`
- Protocol JSON: `progress/evidence/n10-integrated-calibration-protocol-20261028-415.json`
- Prepared driver: `artifacts/n10-prepared/n10-20261028-415-speed040-yawcap010-compacttrace-calibration/n10-runtime-driver.sh`
- Prelaunch identity is written only after the stack launches and the grounded PX4/bridge readback passes.

## Current status

Prepared only. No PX4 goal has been submitted and no flight has started.
