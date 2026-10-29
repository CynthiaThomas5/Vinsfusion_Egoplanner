# N10.3 #378 protocol

## User constraints

Continue and complete N10. The PX4 speed value should be evidence-based; a sample-selection window is not an operational speed cap. Before flight, audit project-added health protections and remove them; preserve the already-audited upstream and PX4-native behavior.

## Evidence and decision

#377 used the same runtime, planner and spawn but PX4 horizontal speed peaked at 0.6478956 m/s, below the frozen [0.70,0.80] m/s measurement trigger. The EGO reference peaked at 0.715213 m/s. The navigation action completed before the trigger, so no caller-cancel or stop sample was obtained. The run ended safely, with zero prohibited contacts and independent landed/disarmed/control-disabled/zero-control readback.

As-of matching the #377 valid PX4 local-position stream against the latest same-goal, same-epoch READY command found 110 samples in [0.60,0.66] m/s. The first candidate was 0.601296 m/s at sim time 349.528 s. #378 changes only the trigger window to [0.60,0.66] m/s; planner, route, spawn, runtime fingerprint, observers and stop-band criteria remain fixed.

## Frozen protocol

- Runtime source/install SHA: `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`.
- Planner: horizon 5 m, max velocity 0.8 m/s/axis, max acceleration 0.25 m/s^2/axis, official_ego.
- Spawn: [-8,0,0.3,0,0,0]; one +16m/+0.10m/+0.20rad goal.
- Trigger: actual PX4 horizontal speed [0.60,0.66] m/s with same-goal READY command and valid PX4 position.
- Stop band, truth coverage, contact and terminal-readback criteria unchanged from #377.

## Status

Protocol was frozen before SITL. The container started, but the first run-local identity check exited before preflight or goal because `n09-runtime-contract-current.json` did not yet exist. A six-second independent readback confirmed DISABLED, landed, disarmed, control-disabled and zero control. The run-local driver now runs the hash-verified `runtime_manifest.py` before comparing current and frozen fingerprints. The updated driver and a pre-goal addendum are frozen; the flight goal has not been sent. N10.3 remains incomplete, followed by N10.4–N10.7.
