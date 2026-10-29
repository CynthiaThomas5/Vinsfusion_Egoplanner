# N10.3/#371 result: cylinder observation did not cover the contact

## Result

`n10-20261027-371-cylinder-observation-live-obstacle` is a failed diagnostic, not an N10/N12 pass. The PX4 goal was sent and the vehicle reached ACTIVE, but the flight action ended with `caller_cancel` after the bridge reported `external_odometry_stale`. The container was stopped only after independent readback showed landed, disarmed, control disabled, and zero control samples.

## Recorded events

- Gazebo acknowledged insertion of `n10_live_replan_box` at sim time `245.020 s`, `12.012 s` after the goal began. A replacement spline was seen; the box ROI had 8 cloud samples with a maximum of 536 points.
- The contact observer recorded 1 prohibited contact event. At sim time `252.832 s`, rotor 2 contacted `unit_cylinder_0`; maximum reported penetration was `0.000106950 m`.
- The added camera/cloud/query observer was aimed at `unit_cylinder_4` (world center `(-2.75559, -2.44735, 0.5) m`), while the contact was with `unit_cylinder_0` (world center `(-1.47322, 3.48874, 0.5) m`). Consequently it saved zero cylinder-specific images, ROI samples, or occupancy queries. The existing run cannot establish whether the actual contact cylinder appeared in the camera or EGO occupied map.

## Disposition

Keep the contact as a failure and do not infer a map/perception root cause from the missing cylinder observations. The next diagnostic is #372: target the observed `unit_cylinder_0`, remove the project-added numeric age gates authorized by the user, and retain the same goal, world, box, trigger, and EGO parameters.

Evidence is stored in `artifacts/runs/n10-20261027-371-cylinder-observation-live-obstacle/`; key file SHA-256 values are in [n10-live-obstacle-cylinder-observation-result-20261027-371.json](n10-live-obstacle-cylinder-observation-result-20261027-371.json). Runtime contract: `9c2f704da0904fabe62925d8526f529c13ce9fbc5ed058d5cf91be9479b6ede6`.
